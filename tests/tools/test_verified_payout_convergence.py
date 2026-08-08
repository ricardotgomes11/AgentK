import unittest
import tempfile
import json
from pathlib import Path
from verified_payout_convergence import VerifiedPayoutConvergenceEngine

class TestVerifiedPayoutConvergence(unittest.TestCase):
    def test_multi_node_payout_convergence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "payout_convergence.log"
            engine = VerifiedPayoutConvergenceEngine(log_path=log_path)
            
            res = engine.execute_and_verify_paid_outcome(
                recipient_id="user_123",
                recipient_name="Ricardo Gomes",
                amount_cents=25000,
                payment_provider="Mercury_ACH"
            )
            
            self.assertTrue(res["is_converged"])
            self.assertEqual(res["paid_amount_usd"], 250.0)
            self.assertEqual(res["payment_provider"], "Mercury_ACH")
            self.assertTrue(res["provider_reference"].startswith("REF_MERCURY_ACH_"))
            self.assertTrue("attestation_hash" in res)
            self.assertEqual(len(res["trace"]), 5)
            
            # Check convergence log
            self.assertTrue(log_path.exists())
            log_data = json.loads(log_path.read_text().strip())
            self.assertEqual(log_data["transaction_id"], res["transaction_id"])
            self.assertTrue(log_data["is_converged"])

if __name__ == "__main__":
    unittest.main()
