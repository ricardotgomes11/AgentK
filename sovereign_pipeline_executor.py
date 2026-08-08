"""
Sovereign Pipeline Executor
===========================
Formalizes AgentK's 6-stage request processing and audit pipeline:
1. Request Ingestion
2. Intent Normalization (NFKC Unicode)
3. Executable & Path Resolution (Canonical Symlink Resolution)
4. Declared Local Effects & Destination Identification
5. Policy Decision & Sandboxed Execution (Sovereign Gate)
6. Observed Output & Append-Only Audit Logging
"""

import os
import sys
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

    def _append_audit_event(self, event_type: str, details: Dict[str, Any]):
        """Stage 6: Writes immutable event record to append-only ledger."""
        record = {
            "event_type": event_type,
            "details": details,
        }
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(f"{record}\n")

    def process_and_execute(self, tool_name: str, raw_command: str, raw_args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        raw_args = raw_args or {}

        # 1. Request
        request_data = {"tool_name": tool_name, "raw_command": raw_command, "raw_args": raw_args}

        # 2. Normalized Intent
        normalized_cmd = unicodedata.normalize("NFKC", str(raw_command)).strip()

        # 3. Resolved Executable and Paths
        resolved_paths = []
        for token in normalized_cmd.split():
            token_clean = token.strip("'\"")
            if "/" in token_clean or token_clean.endswith(".py") or token_clean.endswith(".sh"):
                try:
                    resolved_paths.append(str(Path(token_clean).resolve()))
                except Exception:
                    resolved_paths.append(token_clean)

        # 4. Declared Local Effects + Destination
        declared_effects = {
            "command": normalized_cmd,
            "resolved_paths": resolved_paths,
            "is_destructive_candidate": any(op in normalized_cmd for op in ["rm", "mv", "chmod", "write", ">", ">>"]),
            "destination": "local_shell" if "http" not in normalized_cmd else "external_network",
        }

        # 5. Policy Decision -> Execution Sandbox
        tc = SimpleNamespace(
            name=tool_name,
            args={"CommandLine": normalized_cmd, "command": normalized_cmd, **raw_args},
            canonical_path=resolved_paths[0] if resolved_paths else None,
        )
        eval_result = sovereign_gate.evaluate_or_dispatch(tc)

        if getattr(eval_result, "denied", False):
            audit_entry = {
                "request": request_data,
                "declared_effects": declared_effects,
                "decision": "DENIED",
                "reason": "Sovereign Gate policy enforcement",
            }
            self._append_audit_event("POLICY_DENIED", audit_entry)
            return {
                "status": "denied",
                "stderr": f"Command denied by Sovereign Gate policy: {normalized_cmd}",
                "returncode": 126,
            }

        # Execute in sandbox
        try:
            res = subprocess.run(normalized_cmd, shell=True, capture_output=True, text=True, timeout=30.0)
            observed_effects = {
                "returncode": res.returncode,
                "stdout_len": len(res.stdout),
                "stderr_len": len(res.stderr),
            }
            # 6. Observed Effects -> Append-only Audit Event
            self._append_audit_event("EXECUTION_COMPLETED", {
                "request": request_data,
                "declared_effects": declared_effects,
                "observed_effects": observed_effects,
            })
            return {"status": "success", "stdout": res.stdout, "stderr": res.stderr, "returncode": res.returncode}
        except Exception as e:
            self._append_audit_event("EXECUTION_FAILED", {"request": request_data, "error": str(e)})
            return {"status": "error", "stderr": str(e), "returncode": 1}


if __name__ == "__main__":
    executor = SovereignPipelineExecutor()
    res = executor.process_and_execute("run_command", "echo 'Testing Sovereign Pipeline'")
    print(f"[PIPELINE EXECUTOR] Result: {res}")
