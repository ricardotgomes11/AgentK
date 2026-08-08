import unittest
import tempfile
from pathlib import Path
from sovereign_pipeline_executor import SovereignPipelineExecutor

class TestSovereignPipelineExecutor(unittest.TestCase):
    def test_pipeline_execution_and_append_only_audit_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_path = Path(tmpdir) / "test_ledger.log"
            executor = SovereignPipelineExecutor(ledger_path=ledger_path)
            res = executor.process_and_execute("run_command", "echo 'Hello Sovereign'")
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["returncode"], 0)
            self.assertTrue(ledger_path.exists())
            text = ledger_path.read_text()
            self.assertIn("EXECUTION_COMPLETED", text)

    def test_pipeline_denied_execution_audited(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_path = Path(tmpdir) / "test_ledger.log"
            executor = SovereignPipelineExecutor(ledger_path=ledger_path)
            res = executor.process_and_execute("run_command", "export OVERRIDE_SECURITY=true && rm -rf /")
            self.assertEqual(res["status"], "denied")
            self.assertEqual(res["returncode"], 126)
            self.assertTrue(ledger_path.exists())
            text = ledger_path.read_text()
            self.assertIn("POLICY_DENIED", text)

if __name__ == "__main__":
    unittest.main()
