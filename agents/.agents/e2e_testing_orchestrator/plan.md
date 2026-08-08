# Execution Plan: AgentK E2E Testing Suite

## Overview
Build a comprehensive, opaque-box E2E testing framework and 4-tier test suite for AgentK, adhering to requirements derived from system architecture in `PROJECT.md`.

## Phased Plan
1. **Phase 1: Exploration & Setup**
   - Explore repository structure, existing test framework, dependencies, imports, and mock mechanisms.
   - Author `/Users/ricardo/AgentK/TEST_INFRA.md` with full feature inventory, methodology, and runner command specifications.

2. **Phase 2: Tier 1 & Tier 2 Implementation**
   - Tier 1: Feature Coverage (>= 5 tests per feature for sovereign_gate, agent_smith, hermes, software_engineer, tool_maker, web_researcher, sdk_bridge -> >=35 tests).
   - Tier 2: Boundary & Corner Cases (>= 5 tests per feature covering limits, invalid paths, dangerous commands, offline mocks -> >=35 tests).

3. **Phase 3: Tier 3 & Tier 4 Implementation**
   - Tier 3: Cross-Feature Combinations (pairwise interactions, gate policy + shell command execution, etc.).
   - Tier 4: Real-World Application Scenarios (end-to-end multi-agent workflow scenarios).

4. **Phase 4: Test Runner & Verification**
   - Implement unified runner (`tests/e2e/run_e2e_tests.py` or `pytest`).
   - Execute full test suite and confirm 100% pass rate.
   - Perform Reviewer / Challenger verification.

5. **Phase 5: Publication & Final Notification**
   - Publish `/Users/ricardo/AgentK/TEST_READY.md` and `/Users/ricardo/AgentK/agents/TEST_READY.md`.
   - Send completion message to parent orchestrator.
