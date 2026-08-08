# Orchestration Plan: AgentK / agents

## Objective
Analyze the existing codebase in `/Users/ricardo/AgentK/agents/`, determine project scope and requirements, decompose into milestones, and orchestrate subagents (Explorer, Worker, Reviewer, Challenger, Auditor, E2E Testing Sub-orchestrator) to build, test, and verify the project.

## Phased Approach

### Phase 1: Exploration & Architecture Definition
1. Dispatch 3 Explorers (`teamwork_preview_explorer`) in parallel to thoroughly explore:
   - Codebase structure, Python modules (`agent_smith.py`, `hermes.py`, `sdk_bridge.py`, `software_engineer.py`, `sovereign_gate.py`, `tool_maker.py`, `web_researcher.py`), existing tests, dependencies, and configuration.
   - Any embedded requirements, TODO comments, specs, or draft requirements in `ORIGINAL_REQUEST.md`.
2. Synthesize Explorer reports into `PROJECT.md` at project root. Define module architecture, interface contracts, code layout, and implementation milestones.

### Phase 2: Dual-Track Execution Setup
1. **E2E Testing Track**: Dispatch E2E Testing Orchestrator subagent (`self` or `teamwork_preview_orchestrator`) to build `TEST_INFRA.md`, E2E test runner, and test cases covering Tiers 1–4, publishing `TEST_READY.md`.
2. **Implementation Track**: For each milestone defined in `PROJECT.md`, execute the Explorer -> Worker -> Reviewer -> Challenger -> Forensic Auditor verification loop.

### Phase 3: Verification & Hardening (Final Milestone)
1. **Phase 1 (E2E Test Pass)**: Verify 100% pass on Tiers 1-4 E2E tests.
2. **Phase 2 (Adversarial Coverage Hardening)**: Challenger -> Worker -> Reviewer loop for Tier 5 white-box coverage gaps.
3. **Forensic Integrity Verification**: Ensure all code implementations are genuine and pass audit.

### Phase 4: Final Reporting & Handoff
1. Re-verify all artifacts and issue final report to parent/user.
