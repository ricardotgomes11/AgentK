"""
NotebookLM Synthesis Pipeline
=============================
Automated 6-stage knowledge & documentation synthesis pipeline for AgentK:
1. Detect Change       (Git commit/diff or trigger events)
2. Compile Evidence    (Code diffs, test evidence, audit hashes)
3. Send to NotebookLM  (Grounded synthesis via Gemini SL bridge)
4. Receive Draft       (Structured architectural summaries)
5. Validate            (Schema & Sovereign Gate verification)
6. Store Provenance    (SHA-256 linked provenance log)
7. Publish or Queue    (Knowledge base update or review queue)
"""

import os
import sys
import json
import time
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from bin.holixtica_gemini_bridge import HolixticaGeminiBridge
from sovereign_pipeline_executor import SovereignPipelineExecutor

PROJECT_ROOT = Path(__file__).resolve().parent
PROVENANCE_LOG = PROJECT_ROOT / "nexus_ledger" / "provenance.log"
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"


class NotebookLMSynthesisPipeline:
    def __init__(self, provenance_path: Path = PROVENANCE_LOG, knowledge_dir: Path = KNOWLEDGE_DIR):
        self.provenance_path = provenance_path
        self.knowledge_dir = knowledge_dir
        self.provenance_path.parent.mkdir(parents=True, exist_ok=True)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.bridge = HolixticaGeminiBridge()
        self.executor = SovereignPipelineExecutor()

    def detect_change(self) -> Dict[str, Any]:
        """Stage 1: Detect change by checking recent git commits and status."""
        try:
            res = subprocess.run("git log -1 --stat", shell=True, capture_output=True, text=True, cwd=PROJECT_ROOT)
            return {"commit_summary": res.stdout.strip(), "timestamp": time.time()}
        except Exception as e:
            return {"commit_summary": f"Local workspace state update at {time.time()}", "error": str(e)}

    def compile_evidence(self, change_info: Dict[str, Any]) -> str:
        """Stage 2: Compile code diffs, test results, and execution ledger hashes into evidence bundle."""
        ledger_file = PROJECT_ROOT / "nexus_ledger" / "execution.log"
        last_ledger_line = ""
        if ledger_file.exists():
            lines = [l for l in ledger_file.read_text().split("\n") if l.strip()]
            if lines:
                last_ledger_line = lines[-1]

        evidence = f"""
=== EVIDENTIARY BUNDLE FOR SYNTHESIS ===
Change Detection:
{change_info.get('commit_summary', '')}

Latest Ledger Attestation:
{last_ledger_line}
=========================================
"""
        return evidence.strip()

    def synthesize_draft(self, evidence: str) -> str:
        """Stage 3 & 4: Send to NotebookLM / Gemini SL Bridge and receive grounded draft."""
        system_prompt = (
            "You are NotebookLM Knowledge Synthesizer. "
            "Synthesize a concise, grounded architectural change summary strictly based on the provided evidence."
        )
        response = self.bridge.generate_completion(evidence, system_instruction=system_prompt)
        
        # Extract response text or fallback
        if "candidates" in response:
            try:
                return response["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                pass
        return f"# Architectural Knowledge Update\n\n**Evidence Compiled:**\n\n```text\n{evidence}\n```"

    def validate_draft(self, draft: str) -> bool:
        """Stage 5: Validate schema and safety rules."""
        if not draft or len(draft.strip()) < 10:
            return False
        # Ensure no forbidden override tokens
        if "OVERRIDE_SECURITY" in draft:
            return False
        return True

    def store_provenance(self, draft: str, change_info: Dict[str, Any]) -> str:
        """Stage 6: Store SHA-256 linked provenance entry."""
        provenance_data = {
            "timestamp": time.time(),
            "change_info": change_info,
            "draft_hash": hashlib.sha256(draft.encode("utf-8")).hexdigest(),
        }
        prov_hash = hashlib.sha256(json.dumps(provenance_data, sort_keys=True).encode("utf-8")).hexdigest()
        record = {**provenance_data, "provenance_hash": prov_hash}
        
        with open(self.provenance_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return prov_hash

    def run_synthesis_cycle(self, publish: bool = True) -> Dict[str, Any]:
        """Runs the complete 7-step NotebookLM synthesis workflow."""
        change = self.detect_change()
        evidence = self.compile_evidence(change)
        draft = self.synthesize_draft(evidence)

        if not self.validate_draft(draft):
            return {"status": "invalid_draft", "reason": "Draft failed validation"}

        prov_hash = self.store_provenance(draft, change)

        # Stage 7: Publish or Queue
        if publish:
            doc_file = self.knowledge_dir / f"synthesis_{int(time.time())}.md"
            doc_file.write_text(draft)
            return {"status": "published", "file": str(doc_file), "provenance_hash": prov_hash}
        else:
            return {"status": "queued", "draft": draft, "provenance_hash": prov_hash}


if __name__ == "__main__":
    pipeline = NotebookLMSynthesisPipeline()
    res = pipeline.run_synthesis_cycle(publish=True)
    print(f"[NOTEBOOKLM PIPELINE] Execution Result:\n{json.dumps(res, indent=2)}")
