---
name: financial-settlement-verifier
description: >
  Verifies federated multi-node mesh orchestration convergence and enforces
  5-field 1-to-1 account reconciliation matching for production SETTLED financial finality.
---

# Financial Settlement Verifier

## Overview

Packaging the complete AgentK multi-node mesh orchestration and financial finality verification workflow.
Distinguishes between **mesh convergence** (`is_mesh_converged` = node agreement) and **financial finality** (`financially_final` = signed provider confirmation + bank statement reconciliation).

## Financial Finality Invariant

A transaction is marked `financially_final = True` if and only if:

$$\text{financially\_final} = \text{production} \land \text{signature\_verified} \land \text{provider\_settled} \land \text{seven\_field\_match} \land \text{within\_settlement\_window} \land \neg\text{reversed}$$

Where:
```python
seven_field_match = (
    rec.provider_transaction_id == receipt.provider_transaction_id
    and rec.amount_cents == receipt.amount_cents
    and rec.currency == receipt.currency
    and rec.recipient_account_ref == receipt.recipient_account_ref
    and rec.direction == "OUTBOUND"
    and rec.provider_account_id == receipt.provider_account_id
)
within_settlement_window = abs(rec.settled_timestamp - receipt.event_timestamp) <= max_window_seconds
not_reversed = not receipt.is_reversed and receipt.status not in {"RETURNED", "REVERSED", "FAILED", "CHARGEBACK"}
```

## Quick Start

```python
from verified_payout_convergence import VerifiedPayoutConvergenceEngine, ProviderReceipt, ReconciliationRecord

engine = VerifiedPayoutConvergenceEngine()

# 1. Evaluate Simulated Mesh Convergence
sim_res = engine.execute_and_verify_paid_outcome("user_123", "Ricardo Gomes", 25000, "Mercury_ACH")
assert sim_res["is_mesh_converged"] is True
assert sim_res["financially_final"] is False

# 2. Evaluate Production SETTLED Financial Finality
rec = ReconciliationRecord(
    reconciliation_id="rec_bank_statement_001",
    provider_transaction_id="tx_prod_mercury_12345",
    amount_cents=25000,
    currency="USD",
    recipient_account_ref="acc_mercury_gomes",
    direction="OUTBOUND",
)
receipt = ProviderReceipt(
    environment="production",
    status="SETTLED",
    provider_transaction_id="tx_prod_mercury_12345",
    amount_cents=25000,
    currency="USD",
    recipient_account_ref="acc_mercury_gomes",
    raw_signature_digest="sha256:abc123def456",
    signature_verified=True,
    reconciliation=rec,
)
prod_res = engine.execute_and_verify_paid_outcome("user_123", "Ricardo Gomes", 25000, "Mercury_RTP", provider_receipt=receipt)
assert prod_res["financially_final"] is True
```

## Status Vocabulary

- **`SIMULATED`**: Test fixture or internal mock response.
- **`PENDING`**: Payment instruction created.
- **`PROVIDER_ACCEPTED`**: Authenticated provider acknowledged payment instruction.
- **`SETTLED`**: Provider response and 5-field bank reconciliation match.
- **`RETURNED`**: Funds reversed, returned, or failed.

## Common Pitfalls

- **Do Not Trust Simulated Identifiers for Financial Claims**: `SIMULATED` confirms mesh orchestration, not bank settlement.
- **No Raw Credentials in Ledger**: Attestation ledgers record only SHA-256 digests (`provider_transaction_id`, `raw_signature_digest`, `reconciliation_id`, `timestamp`), never raw account keys or secrets.
