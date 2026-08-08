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

    def test_production_financial_finality_and_reversal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "payout_convergence.log"
            engine = VerifiedPayoutConvergenceEngine(log_path=log_path)
            now = 1700000000.0

            rec = ReconciliationRecord(
                reconciliation_id="rec_001",
                provider_transaction_id="tx_mercury_prod_001",
                amount_cents=50000,
                currency="USD",
                recipient_account_ref="acc_mercury_gomes",
                provider_account_id="acct_mercury_biz_01",
                direction="OUTBOUND",
                settled_timestamp=now + 300.0,  # 5 minutes later
            )

            prod_receipt = ProviderReceipt(
                environment="production",
                status="SETTLED",
                provider_transaction_id="tx_mercury_prod_001",
                amount_cents=50000,
                currency="USD",
                recipient_account_ref="acc_mercury_gomes",
                provider_account_id="acct_mercury_biz_01",
                raw_signature_digest="sha256:abc123def456",
                signature_verified=True,
                event_timestamp=now,
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

            # Test Out of Window Failure (e.g. 48h late reconciliation)
            late_rec = ReconciliationRecord(
                reconciliation_id="rec_late_002",
                provider_transaction_id="tx_mercury_prod_001",
                amount_cents=50000,
                currency="USD",
                recipient_account_ref="acc_mercury_gomes",
                provider_account_id="acct_mercury_biz_01",
                direction="OUTBOUND",
                settled_timestamp=now + 172800.0,  # 48 hours later (> 24h window)
            )
            self.assertFalse(prod_receipt.matches_reconciliation(late_rec, max_window_seconds=86400.0))

            # Test Append-Only Reversal Counter-Event
            rev_res = engine.append_reversal_counter_event(
                transaction_id=res["transaction_id"],
                reversal_status="RETURNED",
                reversal_reason="ACH_R01_INSUFFICIENT_FUNDS",
                provider_receipt=prod_receipt,
            )

            self.assertFalse(rev_res["financially_final"])
            self.assertFalse(prod_receipt.financially_final)
            self.assertTrue(prod_receipt.is_reversed)
            self.assertEqual(prod_receipt.status, "RETURNED")

            # Test Replay Log from Origin to Present
            replayed_state = engine.replay_ledger_state()
            self.assertIn(res["transaction_id"], replayed_state)
            replayed_tx = replayed_state[res["transaction_id"]]
            self.assertFalse(replayed_tx["financially_final"])
            self.assertTrue(replayed_tx["is_reversed"])
            self.assertEqual(replayed_tx["status"], "RETURNED")
            self.assertEqual(replayed_tx["origin_line"], 1)
            self.assertEqual(replayed_tx["last_replayed_line"], 2)

    def test_identity_equations_proof(self):
        """Formally verifies:
        Equation 1: snapshot(state at line k) == replay(events 1..k)
        Equation 2: replay(events 1..N) == current materialized view
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "payout_convergence.log"
            engine = VerifiedPayoutConvergenceEngine(log_path=log_path)
            now = 1700000000.0

            rec = ReconciliationRecord(
                reconciliation_id="rec_001",
                provider_transaction_id="tx_mercury_prod_001",
                amount_cents=50000,
                currency="USD",
                recipient_account_ref="acc_mercury_gomes",
                provider_account_id="acct_mercury_biz_01",
                direction="OUTBOUND",
                settled_timestamp=now + 300.0,
            )

            prod_receipt = ProviderReceipt(
                environment="production",
                status="SETTLED",
                provider_transaction_id="tx_mercury_prod_001",
                amount_cents=50000,
                currency="USD",
                recipient_account_ref="acc_mercury_gomes",
                provider_account_id="acct_mercury_biz_01",
                raw_signature_digest="sha256:abc123def456",
                signature_verified=True,
                event_timestamp=now,
                reconciliation=rec,
            )

            # Event 1: Initial Settlement
            res1 = engine.execute_and_verify_paid_outcome(
                recipient_id="user_123",
                recipient_name="Ricardo Gomes",
                amount_cents=50000,
                payment_provider="Mercury_RTP",
                provider_receipt=prod_receipt,
            )

            # Equation 1 Check at Line 1
            snapshot_k1 = engine.replay_events_up_to_line(1)
            replay_1 = engine.replay_ledger_state()
            self.assertEqual(snapshot_k1, replay_1)
            self.assertTrue(snapshot_k1[res1["transaction_id"]]["financially_final"])

            # Event 2: Append Counter-Event Reversal
            engine.append_reversal_counter_event(
                transaction_id=res1["transaction_id"],
                reversal_status="RETURNED",
                reversal_reason="ACH_R01_INSUFFICIENT_FUNDS",
                provider_receipt=prod_receipt,
            )

            # Equation 1 Check at Line 1 (Past snapshot preserved)
            snapshot_k1_after = engine.replay_events_up_to_line(1)
            self.assertTrue(snapshot_k1_after[res1["transaction_id"]]["financially_final"])

            # Equation 2 Check at Line 2 (Materialized View == Full Replay 1..N)
            replay_1_to_N = engine.replay_ledger_state()
            materialized_view = engine.get_materialized_view()
            self.assertEqual(replay_1_to_N, materialized_view)
            self.assertFalse(materialized_view[res1["transaction_id"]]["financially_final"])

if __name__ == "__main__":
    unittest.main()
