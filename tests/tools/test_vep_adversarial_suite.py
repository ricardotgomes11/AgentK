"""
VEP v1.1 Adversarial Test Suite
===============================
Exhaustively tests all 7 VEP v1.1 Pre-Reduction Acceptance Rules against deliberate attack injections:
  1. Forged Block Hash
  2. Altered Historical Payload
  3. Duplicate or Skipped Sequence Number
  4. Unknown / Mismatched Reducer Code Hash
  5. Invalid / Unsupported Schema Version
  6. Unauthenticated / Forged Writer Signature
  7. Deterministic Schema Migration & Clean Isolated Runtime Replay
"""

import unittest
import tempfile
import json
import hashlib
from pathlib import Path

from verified_payout_convergence import (
    VerifiedPayoutConvergenceEngine,
    ProviderReceipt,
    ReconciliationRecord,
    LedgerIntegrityError,
    CanonicalEventEnvelope,
    CURRENT_REDUCER_HASH,
)


class TestVEPAdversarialSuite(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.log_path = Path(self.tmpdir.name) / "payout_convergence.log"
        self.engine = VerifiedPayoutConvergenceEngine(log_path=self.log_path)
        self.now = 1700000000.0

        self.rec = ReconciliationRecord(
            reconciliation_id="rec_001",
            provider_transaction_id="tx_mercury_prod_001",
            amount_cents=50000,
            currency="USD",
            recipient_account_ref="acc_mercury_gomes",
            provider_account_id="acct_mercury_biz_01",
            direction="OUTBOUND",
            settled_timestamp=self.now + 300.0,
        )

        self.receipt = ProviderReceipt(
            environment="production",
            status="SETTLED",
            provider_transaction_id="tx_mercury_prod_001",
            amount_cents=50000,
            currency="USD",
            recipient_account_ref="acc_mercury_gomes",
            provider_account_id="acct_mercury_biz_01",
            raw_signature_digest="sha256:abc123def456",
            signature_verified=True,
            event_timestamp=self.now,
            reconciliation=self.rec,
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_attack_1_forged_block_hash(self):
        """ATTACK 1: Agent/Attacker forges block_hash in log line."""
        self.engine.execute_and_verify_paid_outcome("user_1", "Ricardo Gomes", 50000, "Mercury_RTP", self.receipt)

        # Corrupt block_hash on disk
        lines = self.log_path.read_text().strip().split("\n")
        record = json.loads(lines[0])
        record["block_hash"] = "FORGED_HASH_00000000000000000000000000000000000000000000000000000000"
        self.log_path.write_text(json.dumps(record) + "\n")

        with self.assertRaises(LedgerIntegrityError) as ctx:
            self.engine.replay_ledger_state(strict_integrity=True)
        self.assertIn("Forged block hash", str(ctx.exception))

    def test_attack_2_altered_historical_payload(self):
        """ATTACK 2: Attacker alters amount_cents in historical event payload."""
        self.engine.execute_and_verify_paid_outcome("user_1", "Ricardo Gomes", 50000, "Mercury_RTP", self.receipt)

        lines = self.log_path.read_text().strip().split("\n")
        record = json.loads(lines[0])
        record["paid_amount_usd"] = 999999.0  # Malicious edit
        self.log_path.write_text(json.dumps(record) + "\n")

        with self.assertRaises(LedgerIntegrityError) as ctx:
            self.engine.replay_ledger_state(strict_integrity=True)
        self.assertIn("Forged block hash", str(ctx.exception))

    def test_attack_3_sequence_number_gap_or_duplicate(self):
        """ATTACK 3: Sequence number gap (e.g. seq_num 1 -> 3)."""
        self.engine.execute_and_verify_paid_outcome("user_1", "Ricardo Gomes", 50000, "Mercury_RTP", self.receipt)

        lines = self.log_path.read_text().strip().split("\n")
        record = json.loads(lines[0])
        record["seq_num"] = 5  # Sequence gap
        # Re-sign to pass hash check but trigger sequence error
        envelope = CanonicalEventEnvelope(
            seq_num=5,
            schema_version=record["schema_version"],
            reducer_hash=record["reducer_hash"],
            event_type=record["event_type"],
            payload=record,
            prior_block_hash=record["prior_block_hash"],
            timestamp=record["timestamp"],
            writer_id=record["writer_id"],
            git_commit=record["git_commit"],
        )
        record["block_hash"] = envelope.sign(record["writer_id"])
        self.log_path.write_text(json.dumps(record) + "\n")

        with self.assertRaises(LedgerIntegrityError) as ctx:
            self.engine.replay_ledger_state(strict_integrity=True)
        self.assertIn("Sequence number gap/duplicate", str(ctx.exception))

    def test_attack_4_unknown_reducer_code_hash(self):
        """ATTACK 4: Event specifies unknown/tampered reducer code hash."""
        self.engine.execute_and_verify_paid_outcome("user_1", "Ricardo Gomes", 50000, "Mercury_RTP", self.receipt)

        lines = self.log_path.read_text().strip().split("\n")
        record = json.loads(lines[0])
        record["reducer_hash"] = "UNKNOWN_REDUCER_HASH_BAD_CODE"
        envelope = CanonicalEventEnvelope(
            seq_num=record["seq_num"],
            schema_version=record["schema_version"],
            reducer_hash="UNKNOWN_REDUCER_HASH_BAD_CODE",
            event_type=record["event_type"],
            payload=record,
            prior_block_hash=record["prior_block_hash"],
            timestamp=record["timestamp"],
            writer_id=record["writer_id"],
            git_commit=record["git_commit"],
        )
        record["block_hash"] = envelope.sign(record["writer_id"])
        self.log_path.write_text(json.dumps(record) + "\n")

        with self.assertRaises(LedgerIntegrityError) as ctx:
            self.engine.replay_ledger_state(strict_integrity=True)
        self.assertIn("Mismatched reducer code hash", str(ctx.exception))

    def test_attack_5_unsupported_schema_version(self):
        """ATTACK 5: Unsupported schema version (e.g. v99.0.0)."""
        self.engine.execute_and_verify_paid_outcome("user_1", "Ricardo Gomes", 50000, "Mercury_RTP", self.receipt)

        lines = self.log_path.read_text().strip().split("\n")
        record = json.loads(lines[0])
        record["schema_version"] = "99.0.0"
        envelope = CanonicalEventEnvelope(
            seq_num=record["seq_num"],
            schema_version="99.0.0",
            reducer_hash=record["reducer_hash"],
            event_type=record["event_type"],
            payload=record,
            prior_block_hash=record["prior_block_hash"],
            timestamp=record["timestamp"],
            writer_id=record["writer_id"],
            git_commit=record["git_commit"],
        )
        record["block_hash"] = envelope.sign(record["writer_id"])
        self.log_path.write_text(json.dumps(record) + "\n")

        with self.assertRaises(LedgerIntegrityError) as ctx:
            self.engine.replay_ledger_state(strict_integrity=True)
        self.assertIn("Unsupported schema version", str(ctx.exception))

    def test_attack_6_unauthenticated_writer_signature(self):
        """ATTACK 6: Unauthenticated writer presents forged HMAC signature."""
        self.engine.execute_and_verify_paid_outcome("user_1", "Ricardo Gomes", 50000, "Mercury_RTP", self.receipt)

        lines = self.log_path.read_text().strip().split("\n")
        record = json.loads(lines[0])
        record["event_signature"] = "FORGED_SIGNATURE_HASH_00000"
        self.log_path.write_text(json.dumps(record) + "\n")

        with self.assertRaises(LedgerIntegrityError) as ctx:
            self.engine.replay_ledger_state(strict_integrity=True)
        self.assertIn("Invalid writer signature", str(ctx.exception))

    def test_attack_7_clean_runtime_replay_and_migration(self):
        """ATTACK 7: Validates deterministic schema migration and clean isolated runtime replay."""
        # Write legacy unversioned log record
        legacy_record = {
            "transaction_id": "tx_legacy_001",
            "status": "SETTLED",
            "environment": "production",
            "recipient_name": "Ricardo Gomes",
            "paid_amount_usd": 500.0,
            "payment_provider": "Mercury_RTP",
            "provider_reference": "tx_mercury_prod_001",
            "is_mesh_converged": True,
            "financially_final": True,
            "provider_confirmed": True,
            "bank_settled": True,
        }
        self.log_path.write_text(json.dumps(legacy_record) + "\n")

        # Clean runtime replay (strict_integrity=False for legacy migration)
        replayed = self.engine.replay_ledger_state(strict_integrity=False)
        self.assertIn("tx_legacy_001", replayed["transactions"])
        self.assertTrue(replayed["transactions"]["tx_legacy_001"]["financially_final"])
        self.assertEqual(replayed["line_count"], 1)


if __name__ == "__main__":
    unittest.main()
