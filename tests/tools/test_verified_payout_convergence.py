import unittest
import tempfile
import json
from pathlib import Path
from verified_payout_convergence import VerifiedPayoutConvergenceEngine, ProviderReceipt, ReconciliationRecord

class TestVerifiedPayoutConvergence(unittest.TestCase):
    def test_simulated_mesh_convergence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "payout_convergence.log"
            engine = VerifiedPayoutConvergenceEngine(log_path=log_path)
            
            res = engine.execute_and_verify_paid_outcome(
                recipient_id="user_123",
                recipient_name="Ricardo Gomes",
                amount_cents=25000,
                payment_provider="Mercury_ACH"
            )
            
            self.assertTrue(res["is_mesh_converged"])
            self.assertFalse(res["financially_final"])  # SIMULATED is not financially_final
            self.assertEqual(res["status"], "SIMULATED")
            self.assertEqual(res["environment"], "simulated")
            self.assertEqual(res["paid_amount_usd"], 250.0)

    def test_production_financial_finality(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "payout_convergence.log"
            engine = VerifiedPayoutConvergenceEngine(log_path=log_path)

            rec = ReconciliationRecord(
                reconciliation_id="rec_001",
                provider_transaction_id="tx_mercury_prod_001",
                amount_cents=50000,
                currency="USD",
                recipient_account_ref="acc_mercury_gomes",
                direction="OUTBOUND",
            )

            prod_receipt = ProviderReceipt(
                environment="production",
                status="SETTLED",
                provider_transaction_id="tx_mercury_prod_001",
                amount_cents=50000,
                currency="USD",
                recipient_account_ref="acc_mercury_gomes",
                raw_signature_digest="sha256:abc123def456",
                signature_verified=True,
                reconciliation=rec,
            )

            res = engine.execute_and_verify_paid_outcome(
                recipient_id="user_123",
                recipient_name="Ricardo Gomes",
                amount_cents=50000,
                payment_provider="Mercury_RTP",
                provider_receipt=prod_receipt,
            )

            self.assertTrue(res["is_mesh_converged"])
            self.assertTrue(res["financially_final"])
            self.assertTrue(res["provider_confirmed"])
            self.assertTrue(res["bank_settled"])
            self.assertEqual(res["status"], "SETTLED")
            self.assertEqual(res["environment"], "production")

if __name__ == "__main__":
    unittest.main()
