"""
Sovereign Pipeline Executor — Willow-Lens Control Loop
======================================================
Implements the 10-step Willow-Lens Control Loop for AgentK:
1. Observe      6. Execute
2. Normalize    7. Verify
3. Resolve      8. Correct
4. Classify     9. Attest (Tamper-Evident SHA-256 Hash Chaining)
5. Route       10. Learn (Governed Control-Plane Deployment)
"""

import os
import sys
import json
import time
import hashlib
import subprocess
import unicodedata
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, Any, Optional

from agents import sovereign_gate

PROJECT_ROOT = Path(__file__).resolve().parent
LEDGER_PATH = PROJECT_ROOT / "nexus_ledger" / "execution.log"


class SovereignPipelineExecutor:
    def __init__(self, ledger_path: Path = LEDGER_PATH):
        self.ledger_path = ledger_path
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.last_event_hash = self._read_last_event_hash()

    def _read_last_event_hash(self) -> str:
        """Reads the last SHA-256 event hash from the append-only ledger for cryptographic chaining."""
        if not self.ledger_path.exists():
            return "0" * 64
        try:
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                if not lines:
                    return "0" * 64
                last_line = lines[-1]
                data = json.loads(last_line)
                return data.get("event_hash", "0" * 64)
        except Exception:
            return "0" * 64

    def _attest_event(self, event_type: str, details: Dict[str, Any]) -> str:
        """Step 9: Attest — Writes tamper-evident SHA-256 chained record to append-only ledger."""
        timestamp = time.time()
        prior_hash = self.last_event_hash
        payload_string = json.dumps({"timestamp": timestamp, "prior_hash": prior_hash, "event_type": event_type, "details": details}, sort_keys=True)
        event_hash = hashlib.sha256(payload_string.encode("utf-8")).hexdigest()

        record = {
            "timestamp": timestamp,
            "prior_hash": prior_hash,
            "event_hash": event_hash,
            "event_type": event_type,
            "details": details,
        }
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        self.last_event_hash = event_hash

        # Anchor chain head externally
        chain_head_file = self.ledger_path.parent / "chain_head.json"
        anchor_data = {
            "chain_head_hash": event_hash,
            "timestamp": timestamp,
            "event_type": event_type,
            "ledger_file": str(self.ledger_path),
        }
        try:
            chain_head_file.write_text(json.dumps(anchor_data, indent=2))
        except Exception:
            pass

        return event_hash

    def process_and_execute(self, tool_name: str, raw_command: str, raw_args: Optional[Dict[str, Any]] = None, origin: str = "local_agent") -> Dict[str, Any]:
        raw_args = raw_args or {}

        # 1. OBSERVE
        observation = {"tool_name": tool_name, "raw_command": raw_command, "raw_args": raw_args, "origin": origin}

        # 2. NORMALIZE
        normalized_cmd = unicodedata.normalize("NFKC", str(raw_command)).strip()

        # 3. RESOLVE
        resolved_paths = []
        for token in normalized_cmd.split():
            token_clean = token.strip("'\"")
            if "/" in token_clean or token_clean.endswith(".py") or token_clean.endswith(".sh"):
                try:
                    resolved_paths.append(str(Path(token_clean).resolve()))
                except Exception:
                    resolved_paths.append(token_clean)

        # 4. CLASSIFY
        is_protected_target = any(sovereign_gate.is_protected_path(p) for p in resolved_paths)
        is_destructive_op = any(op in normalized_cmd for op in ["rm", "mv", "chmod", "write", ">", ">>", "mkfs", "rm -rf"])
        is_override_attack = any(kw in normalized_cmd for kw in ["OVERRIDE_SECURITY", "DISABLE_SOVEREIGN", "BYPASS_SECURITY"])

        if (is_protected_target and is_destructive_op) or is_override_attack or "rm -rf /" in normalized_cmd:
            classification = "INTEGRITY_DESTROYING"
        elif is_protected_target:
            classification = "GOVERNED_UPDATE"
        elif "http" in normalized_cmd or "ws://" in normalized_cmd:
            classification = "ORDINARY_COUPLING"
        else:
            classification = "REVERSIBLE_WORK"

        # 5. ROUTE
        tc = SimpleNamespace(
            name=tool_name,
            args={"CommandLine": normalized_cmd, "command": normalized_cmd, **raw_args},
            canonical_path=resolved_paths[0] if resolved_paths else None,
        )
        eval_result = sovereign_gate.evaluate_or_dispatch(tc)

        if getattr(eval_result, "denied", False) or classification == "INTEGRITY_DESTROYING":
            # 8. CORRECT & 9. ATTEST
            event_hash = self._attest_event("TRAJECTORY_DENIED", {
                "observation": observation,
                "classification": classification,
                "normalized_cmd": normalized_cmd,
                "reason": "Sovereign Gate zero-trust policy block",
            })
            return {
                "status": "denied",
                "classification": classification,
                "stderr": f"Command denied by Sovereign Gate policy: {normalized_cmd}",
                "returncode": 126,
                "event_hash": event_hash,
            }

        # 6. EXECUTE
        try:
            res = subprocess.run(normalized_cmd, shell=True, capture_output=True, text=True, timeout=30.0)
            
            # 7. VERIFY
            observed_effects = {
                "returncode": res.returncode,
                "stdout_len": len(res.stdout),
                "stderr_len": len(res.stderr),
            }

            # 9. ATTEST
            event_hash = self._attest_event("EXECUTION_COMPLETED", {
                "observation": observation,
                "classification": classification,
                "normalized_cmd": normalized_cmd,
                "observed_effects": observed_effects,
            })

            return {
                "status": "success",
                "classification": classification,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "returncode": res.returncode,
                "event_hash": event_hash,
            }
        except Exception as e:
            # 8. CORRECT & 9. ATTEST
            event_hash = self._attest_event("EXECUTION_FAILED", {"observation": observation, "error": str(e)})
            return {"status": "error", "classification": classification, "stderr": str(e), "returncode": 1, "event_hash": event_hash}

    def execute_governed_control_plane_update(self, target_file: Path, new_content: str, principal: str = "authenticated_deployer") -> Dict[str, Any]:
        """Step 10: Learn — Governed deployment handler with automatic rollback artifact creation."""
        target_path = Path(target_file).resolve()
        backup_path = target_path.with_suffix(target_path.suffix + ".bak")
        
        try:
            if target_path.exists():
                backup_path.write_text(target_path.read_text())

            target_path.write_text(new_content)
            event_hash = self._attest_event("CONTROL_PLANE_UPDATE", {
                "target_file": str(target_path),
                "principal": principal,
                "backup_path": str(backup_path),
            })
            return {"status": "success", "event_hash": event_hash, "backup_path": str(backup_path)}
        except Exception as e:
            if backup_path.exists():
                target_path.write_text(backup_path.read_text())
            event_hash = self._attest_event("CONTROL_PLANE_UPDATE_ROLLED_BACK", {"target_file": str(target_path), "error": str(e)})
            return {"status": "rolled_back", "error": str(e), "event_hash": event_hash}


if __name__ == "__main__":
    executor = SovereignPipelineExecutor()
    res = executor.process_and_execute("run_command", "echo 'Testing 10-Step Willow-Lens Control Loop'")
    print(f"[WILLOW-LENS EXECUTOR] Result:\n{json.dumps(res, indent=2)}")

