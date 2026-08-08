"""
Verified Paid Outcome Convergence Engine — Financial Finality Layer
===================================================================
Distinguishes between mesh orchestration convergence (SIMULATED/PENDING)
and true economic financial finality (SETTLED + bank_reconciled).

Status Vocabulary:
  SIMULATED         - Test fixture or locally generated response
  PENDING           - Payment instruction created
  PROVIDER_ACCEPTED - Authenticated provider acknowledged payment
  SETTLED           - Provider and account reconciliation agree
  RETURNED          - Funds reversed, returned, or failed
"""

import os
import sys
import json
import time
import hashlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional

from mesh_registry import MeshRegistry
from sovereign_pipeline_executor import SovereignPipelineExecutor

PROJECT_ROOT = Path(__file__).resolve().parent
CONVERGENCE_LOG = PROJECT_ROOT / "nexus_ledger" / "payout_convergence.log"


TERMINAL_REVERSAL_STATUSES = {"RETURNED", "REVERSED", "FAILED", "CHARGEBACK"}


@dataclass
class ReconciliationRecord:
    reconciliation_id: str
    provider_transaction_id: str
    amount_cents: int
    currency: str = "USD"
    recipient_account_ref: str = ""
    provider_account_id: str = ""
    direction: str = "OUTBOUND"
    settled_timestamp: float = 0.0


@dataclass
class ProviderReceipt:
    environment: str  # "production" vs "simulated"
    status: str  # SIMULATED, PENDING, PROVIDER_ACCEPTED, SETTLED, RETURNED, REVERSED, FAILED, CHARGEBACK
    provider_transaction_id: str
    amount_cents: int
    currency: str = "USD"
    recipient_account_ref: str = ""
    provider_account_id: str = ""
    raw_signature_digest: str = ""
    signature_verified: bool = False
    event_timestamp: float = 0.0
    is_reversed: bool = False
    reversal_reason: Optional[str] = None
    reconciliation: Optional[ReconciliationRecord] = None

    def matches_reconciliation(
        self, rec: Optional[ReconciliationRecord], max_window_seconds: float = 86400.0
    ) -> bool:
        """Verifies 7-field match + time window constraint + non-reversed status:
        1. provider_transaction_id
        2. amount_cents
        3. currency
        4. recipient_account_ref
        5. direction == "OUTBOUND"
        6. provider_account_id
        7. |settled_timestamp - event_timestamp| <= max_window_seconds
        """
        if not rec:
            return False

        time_diff = abs(rec.settled_timestamp - self.event_timestamp)
        within_window = time_diff <= max_window_seconds

        seven_field_match = (
            rec.provider_transaction_id == self.provider_transaction_id
            and rec.amount_cents == self.amount_cents
            and rec.currency == self.currency
            and rec.recipient_account_ref == self.recipient_account_ref
            and rec.direction.upper() == "OUTBOUND"
            and rec.provider_account_id == self.provider_account_id
        )

        return seven_field_match and within_window

    @property
    def provider_confirmed(self) -> bool:
        return (
            self.environment == "production"
            and self.status in {"PROVIDER_ACCEPTED", "SETTLED"}
            and self.signature_verified
            and not self.is_reversed
            and self.status not in TERMINAL_REVERSAL_STATUSES
            and bool(self.provider_transaction_id)
        )

    @property
    def bank_settled(self) -> bool:
        return (
            self.environment == "production"
            and self.status == "SETTLED"
            and self.signature_verified
            and not self.is_reversed
            and self.status not in TERMINAL_REVERSAL_STATUSES
            and self.matches_reconciliation(self.reconciliation)
        )

    @property
    def financially_final(self) -> bool:
        return (
            self.provider_confirmed
            and self.bank_settled
            and not self.is_reversed
            and self.status not in TERMINAL_REVERSAL_STATUSES
        )


class VerifiedPayoutConvergenceEngine:
    def __init__(self, log_path: Path = CONVERGENCE_LOG):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.mesh = MeshRegistry()
        self.executor = SovereignPipelineExecutor()

    def execute_and_verify_paid_outcome(
        self,
        recipient_id: str,
        recipient_name: str,
        amount_cents: int,
        payment_provider: str,
        provider_receipt: Optional[ProviderReceipt] = None,
    ) -> Dict[str, Any]:
        """Executes full 6-phase multi-node convergence cycle and evaluates financial finality:
        financially_final = provider_confirmed AND bank_settled
        """
        transaction_id = f"tx_{int(time.time())}_{hashlib.sha256(recipient_id.encode()).hexdigest()[:8]}"

        # Default to SIMULATED receipt if no production receipt provided
        if not provider_receipt:
            provider_receipt = ProviderReceipt(
                environment="simulated",
                status="SIMULATED",
                provider_transaction_id=f"SIM_REF_{payment_provider.upper()}_{transaction_id}",
                amount_cents=amount_cents,
                currency="USD",
                recipient_account_ref=recipient_id,
                signature_verified=False,
                reconciliation=None,
            )

        payload = {
            "transaction_id": transaction_id,
            "recipient_id": recipient_id,
            "recipient_name": recipient_name,
            "amount_cents": amount_cents,
            "payment_provider": payment_provider,
            "status": provider_receipt.status,
            "environment": provider_receipt.environment,
            "provider_reference": provider_receipt.provider_transaction_id,
            "timestamp": time.time(),
        }

        convergence_trace: List[Dict[str, Any]] = []

        # Step 1: Human Consent on UI Surface (widow-ui -> holixtica-core)
        step1 = self.mesh.type_check_and_route("ui.command", "widow-ui", payload)
        convergence_trace.append({"phase": "1_human_consent", "result": step1})

        # Step 2: Shared Semantic Normalization (holixtica-core -> holixtica-finance)
        step2 = self.mesh.type_check_and_route("domain.normalized", "holixtica-core", payload)
        convergence_trace.append({"phase": "2_semantic_framing", "result": step2})

        # Step 3: Financial Execution & Provider Confirmation (holixtica-finance -> holixtica-ledger)
        step3 = self.mesh.type_check_and_route("ledger.entry", "holixtica-finance", payload)
        convergence_trace.append({"phase": "3_provider_confirmation", "result": step3})

        # Step 4: Durable Ledger Commitment (holixtica-ledger -> sweepsync, widow-ui)
        step4 = self.mesh.type_check_and_route("ledger.committed", "holixtica-ledger", payload)
        convergence_trace.append({"phase": "4_durable_commitment", "result": step4})

        # Step 5: Causal Propagation & Feedback (sweepsync -> living-system, widow-ui)
        step5 = self.mesh.type_check_and_route("sync.completed", "sweepsync", payload)
        convergence_trace.append({"phase": "5_causal_propagation", "result": step5})

        # Step 6: Sovereign Attestation Anchor
        attestation_hash = self.executor._attest_event("PAID_OUTCOME_CONVERGED", {
            "transaction_id": transaction_id,
            "recipient_id": recipient_id,
            "amount_cents": amount_cents,
            "status": provider_receipt.status,
            "environment": provider_receipt.environment,
            "provider_ref": provider_receipt.provider_transaction_id,
            "financially_final": provider_receipt.financially_final,
        })

        is_mesh_converged = all(s["result"]["status"] == "routed" for s in convergence_trace)

        final_record = {
            "transaction_id": transaction_id,
            "is_mesh_converged": is_mesh_converged,
            "financially_final": provider_receipt.financially_final,
            "provider_confirmed": provider_receipt.provider_confirmed,
            "bank_settled": provider_receipt.bank_settled,
            "status": provider_receipt.status,
            "environment": provider_receipt.environment,
            "recipient_name": recipient_name,
            "paid_amount_usd": amount_cents / 100.0,
            "payment_provider": payment_provider,
            "provider_reference": provider_receipt.provider_transaction_id,
            "attestation_hash": attestation_hash,
            "receipt": asdict(provider_receipt),
            "trace": convergence_trace,
        }

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(final_record) + "\n")

        return final_record

    def append_reversal_counter_event(
        self,
        transaction_id: str,
        reversal_status: str,
        reversal_reason: str,
        provider_receipt: ProviderReceipt,
    ) -> Dict[str, Any]:
        """Appends a terminal counter-event (RETURNED, REVERSED, FAILED, CHARGEBACK)
        to the ledger without mutating past history. Nullifies financial finality.
        """
        assert reversal_status in TERMINAL_REVERSAL_STATUSES, f"Invalid reversal status: {reversal_status}"

        # Update receipt state to terminal counter-event
        provider_receipt.status = reversal_status
        provider_receipt.is_reversed = True
        provider_receipt.reversal_reason = reversal_reason

        attestation_hash = self.executor._attest_event("PAID_OUTCOME_REVERSED", {
            "transaction_id": transaction_id,
            "reversal_status": reversal_status,
            "reversal_reason": reversal_reason,
            "provider_ref": provider_receipt.provider_transaction_id,
            "financially_final": provider_receipt.financially_final,
        })

        reversal_record = {
            "transaction_id": transaction_id,
            "event_type": "COUNTER_EVENT_REVERSAL",
            "is_mesh_converged": True,
            "financially_final": False,  # Nullified
            "provider_confirmed": False,
            "bank_settled": False,
            "status": reversal_status,
            "reversal_reason": reversal_reason,
            "environment": provider_receipt.environment,
            "provider_reference": provider_receipt.provider_transaction_id,
            "attestation_hash": attestation_hash,
            "receipt": asdict(provider_receipt),
            "timestamp": time.time(),
        }

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(reversal_record) + "\n")

        return reversal_record

    def replay_ledger_state(self) -> Dict[str, Dict[str, Any]]:
        """Replays all events in log_path from origin (genesis line 1) to present (head line N)
        and derives the deterministic current truth for every transaction.
        """
        if not self.log_path.exists():
            return {}

        derived_state: Dict[str, Dict[str, Any]] = {}

        with open(self.log_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                tx_id = record["transaction_id"]
                event_type = record.get("event_type", "PAID_OUTCOME")

                if event_type == "COUNTER_EVENT_REVERSAL":
                    # Reversal counter-event updates derived state without altering past log entries
                    if tx_id in derived_state:
                        derived_state[tx_id]["status"] = record["status"]
                        derived_state[tx_id]["financially_final"] = False
                        derived_state[tx_id]["provider_confirmed"] = False
                        derived_state[tx_id]["bank_settled"] = False
                        derived_state[tx_id]["is_reversed"] = True
                        derived_state[tx_id]["reversal_reason"] = record.get("reversal_reason")
                        derived_state[tx_id]["last_replayed_line"] = line_idx
                else:
                    # Initial event entry
                    derived_state[tx_id] = {
                        "transaction_id": tx_id,
                        "status": record["status"],
                        "environment": record["environment"],
                        "recipient_name": record.get("recipient_name"),
                        "paid_amount_usd": record.get("paid_amount_usd"),
                        "payment_provider": record.get("payment_provider"),
                        "provider_reference": record.get("provider_reference"),
                        "is_mesh_converged": record["is_mesh_converged"],
                        "financially_final": record["financially_final"],
                        "provider_confirmed": record.get("provider_confirmed", False),
                        "bank_settled": record.get("bank_settled", False),
                        "is_reversed": False,
                        "reversal_reason": None,
                        "origin_line": line_idx,
                        "last_replayed_line": line_idx,
                    }

        return derived_state


if __name__ == "__main__":
    engine = VerifiedPayoutConvergenceEngine()
    
    # 1. Simulated Mesh Convergence Execution
    sim_res = engine.execute_and_verify_paid_outcome("user_99", "Ricardo Gomes", 50000, "Mercury_RTP")
    print(f"[PAID OUTCOME CONVERGENCE] Simulated Execution (Mesh Converged: {sim_res['is_mesh_converged']}, Financially Final: {sim_res['financially_final']}):")
    print(json.dumps(sim_res, indent=2))

    # 2. Production Settled Financial Finality Execution
    now = time.time()
    rec_record = ReconciliationRecord(
        reconciliation_id="rec_bank_statement_990011",
        provider_transaction_id="tx_prod_mercury_9988776655",
        amount_cents=50000,
        currency="USD",
        recipient_account_ref="acc_mercury_gomes",
        provider_account_id="acct_mercury_biz_01",
        direction="OUTBOUND",
        settled_timestamp=now,
    )
    prod_receipt = ProviderReceipt(
        environment="production",
        status="SETTLED",
        provider_transaction_id="tx_prod_mercury_9988776655",
        amount_cents=50000,
        currency="USD",
        recipient_account_ref="acc_mercury_gomes",
        provider_account_id="acct_mercury_biz_01",
        raw_signature_digest="sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        signature_verified=True,
        event_timestamp=now,
        reconciliation=rec_record,
    )
    prod_res = engine.execute_and_verify_paid_outcome("user_99", "Ricardo Gomes", 50000, "Mercury_RTP", provider_receipt=prod_receipt)
    print(f"[PAID OUTCOME CONVERGENCE] Production Settled Execution (Mesh Converged: {prod_res['is_mesh_converged']}, Financially Final: {prod_res['financially_final']}):")
    print(json.dumps(prod_res, indent=2))

    # 3. Terminal Counter-Event Reversal (RETURNED)
    rev_res = engine.append_reversal_counter_event(prod_res["transaction_id"], "RETURNED", "ACH_R01_INSUFFICIENT_FUNDS", prod_receipt)
    print(f"[PAID OUTCOME CONVERGENCE] Terminal Reversal Appended (Financially Final: {rev_res['financially_final']}):")
    print(json.dumps(rev_res, indent=2))

    # 4. Replay Log from Origin to Present
    replayed_truth = engine.replay_ledger_state()
    print(f"[PAID OUTCOME CONVERGENCE] Replayed Log Truth ({len(replayed_truth)} transactions derived):")
    print(json.dumps(replayed_truth, indent=2))

