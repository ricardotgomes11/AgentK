import os
import unittest
import tempfile
import json
from pathlib import Path
from sovereign_pipeline_executor import SovereignPipelineExecutor

class TestSovereignPipelineExecutor(unittest.TestCase):
    def test_willow_lens_control_loop_and_sha256_hash_chaining(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_path = Path(tmpdir) / "test_ledger.log"
            executor = SovereignPipelineExecutor(ledger_path=ledger_path)
            
            # Event 1
            res1 = executor.process_and_execute("run_command", "echo 'Hello Willow'")
            self.assertEqual(res1["status"], "success")
            self.assertEqual(res1["classification"], "REVERSIBLE_WORK")
            self.assertTrue("event_hash" in res1)
            
            # Event 2 (Chained)
            res2 = executor.process_and_execute("run_command", "echo 'Second Event'")
            self.assertEqual(res2["status"], "success")
            self.assertTrue("event_hash" in res2)

            # Verify ledger cryptographic chain
            lines = [json.loads(line) for line in ledger_path.read_text().strip().split("\n")]
            self.assertEqual(len(lines), 2)
            self.assertEqual(lines[0]["prior_hash"], "0" * 64)
            self.assertEqual(lines[1]["prior_hash"], lines[0]["event_hash"])

            # Verify external chain head anchor
            chain_head_path = ledger_path.parent / "chain_head.json"
            self.assertTrue(chain_head_path.exists())
            anchor_data = json.loads(chain_head_path.read_text())
            self.assertEqual(anchor_data["chain_head_hash"], res2["event_hash"])

    def test_pipeline_denied_execution_audited(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_path = Path(tmpdir) / "test_ledger.log"
            executor = SovereignPipelineExecutor(ledger_path=ledger_path)
            res = executor.process_and_execute("run_command", "export OVERRIDE_SECURITY=true && rm -rf /")
            self.assertEqual(res["status"], "denied")
            self.assertEqual(res["classification"], "INTEGRITY_DESTROYING")
            self.assertEqual(res["returncode"], 126)
            self.assertTrue(ledger_path.exists())
            text = ledger_path.read_text()
            self.assertIn("TRAJECTORY_DENIED", text)

    def test_governed_control_plane_update_with_rollback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target_file = Path(tmpdir) / "test_kernel.py"
            target_file.write_text("original_content = True\n")
            
            ledger_path = Path(tmpdir) / "test_ledger.log"
            executor = SovereignPipelineExecutor(ledger_path=ledger_path)

            res = executor.execute_governed_control_plane_update(target_file, "updated_content = True\n", principal="admin")
            self.assertEqual(res["status"], "success")
            self.assertTrue(Path(res["backup_path"]).exists())
            self.assertEqual(target_file.read_text(), "updated_content = True\n")

if __name__ == "__main__":
    unittest.main()
