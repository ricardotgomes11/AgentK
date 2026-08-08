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


@dataclass
class ReconciliationRecord:
    reconciliation_id: str
    provider_transaction_id: str
    amount_cents: int
    currency: str = "USD"
    recipient_account_ref: str = ""
    direction: str = "OUTBOUND"
    settled_timestamp: float = 0.0


@dataclass
class ProviderReceipt:
    environment: str  # "production" vs "simulated"
    status: str  # SIMULATED, PENDING, PROVIDER_ACCEPTED, SETTLED, RETURNED
    provider_transaction_id: str
    amount_cents: int
    currency: str = "USD"
    recipient_account_ref: str = ""
    raw_signature_digest: str = ""
    signature_verified: bool = False
    reconciliation: Optional[ReconciliationRecord] = None

    def matches_reconciliation(self, rec: Optional[ReconciliationRecord]) -> bool:
        """Verifies amount, currency, direction, account reference, and provider transaction ID match."""
        if not rec:
            return False
        return (
            rec.provider_transaction_id == self.provider_transaction_id
            and rec.amount_cents == self.amount_cents
            and rec.currency == self.currency
            and rec.recipient_account_ref == self.recipient_account_ref
            and rec.direction.upper() == "OUTBOUND"
        )

    @property
    def provider_confirmed(self) -> bool:
        return (
            self.environment == "production"
            and self.status in {"PROVIDER_ACCEPTED", "SETTLED"}
            and self.signature_verified
            and bool(self.provider_transaction_id)
        )

    @property
    def bank_settled(self) -> bool:
        return (
            self.environment == "production"
            and self.status == "SETTLED"
            and self.signature_verified
            and self.matches_reconciliation(self.reconciliation)
        )

    @property
    def financially_final(self) -> bool:
        return self.provider_confirmed and self.bank_settled


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


if __name__ == "__main__":
    engine = VerifiedPayoutConvergenceEngine()
    
    # 1. Simulated Mesh Convergence Execution
    sim_res = engine.execute_and_verify_paid_outcome("user_99", "Ricardo Gomes", 50000, "Mercury_RTP")
    print(f"[PAID OUTCOME CONVERGENCE] Simulated Execution (Mesh Converged: {sim_res['is_mesh_converged']}, Financially Final: {sim_res['financially_final']}):")
    print(json.dumps(sim_res, indent=2))

    # 2. Production Settled Financial Finality Execution
    rec_record = ReconciliationRecord(
        reconciliation_id="rec_bank_statement_990011",
        provider_transaction_id="tx_prod_mercury_9988776655",
        amount_cents=50000,
        currency="USD",
        recipient_account_ref="acc_mercury_gomes",
        direction="OUTBOUND",
        settled_timestamp=time.time(),
    )
    prod_receipt = ProviderReceipt(
        environment="production",
        status="SETTLED",
        provider_transaction_id="tx_prod_mercury_9988776655",
        amount_cents=50000,
        currency="USD",
        recipient_account_ref="acc_mercury_gomes",
        raw_signature_digest="sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        signature_verified=True,
        reconciliation=rec_record,
    )
    prod_res = engine.execute_and_verify_paid_outcome("user_99", "Ricardo Gomes", 50000, "Mercury_RTP", provider_receipt=prod_receipt)
    print(f"[PAID OUTCOME CONVERGENCE] Production Settled Execution (Mesh Converged: {prod_res['is_mesh_converged']}, Financially Final: {prod_res['financially_final']}):")
    print(json.dumps(prod_res, indent=2))

