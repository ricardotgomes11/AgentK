# Scope: E2E Testing Suite Implementation

## Architecture & Methodology
- Opaque-box, requirement-driven E2E test suite.
- 4-Tier Test Case Structure:
  - Tier 1: Feature Coverage (>=5 test cases per core feature across 7 features)
  - Tier 2: Boundary & Corner Cases (>=5 test cases per feature for limits, invalid paths, dangerous commands, offline mocks)
  - Tier 3: Cross-Feature Combinations (pairwise interactions, gate policy + execution, etc.)
  - Tier 4: Real-World Application Scenarios (end-to-end multi-agent workflows)
- Test Infra Document: /Users/ricardo/AgentK/TEST_INFRA.md
- Output signal: /Users/ricardo/AgentK/TEST_READY.md and /Users/ricardo/AgentK/agents/TEST_READY.md

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Test Infrastructure & Specification | Explore repo, create `TEST_INFRA.md` with methodology & feature inventory | None | IN_PROGRESS |
| 2 | Tier 1 & Tier 2 Test Suites | Implement Tier 1 (>=35 tests) & Tier 2 (>=35 tests) in `tests/e2e/` | M1 | PLANNED |
| 3 | Tier 3 & Tier 4 Test Suites | Implement Tier 3 (pairwise) & Tier 4 (real-world E2E scenarios) in `tests/e2e/` | M2 | PLANNED |
| 4 | Test Runner, Verification & Publication | Implement runner (`run_e2e_tests.py`), verify 100% pass, publish `TEST_READY.md` | M3 | PLANNED |
