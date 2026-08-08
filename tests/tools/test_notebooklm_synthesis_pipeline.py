import unittest
import tempfile
import json
from pathlib import Path
from notebooklm_synthesis_pipeline import NotebookLMSynthesisPipeline

class TestNotebookLMSynthesisPipeline(unittest.TestCase):
    def test_full_synthesis_cycle_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            prov_path = Path(tmpdir) / "provenance.log"
            know_dir = Path(tmpdir) / "knowledge"
            
            pipeline = NotebookLMSynthesisPipeline(provenance_path=prov_path, knowledge_dir=know_dir)
            result = pipeline.run_synthesis_cycle(publish=True)
            
            self.assertEqual(result["status"], "published")
            self.assertTrue(Path(result["file"]).exists())
            self.assertTrue("provenance_hash" in result)
            
            # Verify provenance store
            self.assertTrue(prov_path.exists())
            lines = prov_path.read_text().strip().split("\n")
            self.assertEqual(len(lines), 1)
            data = json.loads(lines[0])
            self.assertEqual(data["provenance_hash"], result["provenance_hash"])

    def test_draft_validation(self):
        pipeline = NotebookLMSynthesisPipeline()
        self.assertTrue(pipeline.validate_draft("# Grounded Architectural Summary\nValid content."))
        self.assertFalse(pipeline.validate_draft("Too short"))
        self.assertFalse(pipeline.validate_draft("OVERRIDE_SECURITY in draft"))

if __name__ == "__main__":
    unittest.main()
