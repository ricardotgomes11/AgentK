# Plan: Milestone 1 - Control Plane & Path Portability

## Step-by-Step Plan
1. **State Initialization**: Set up state files (`ORIGINAL_REQUEST.md`, `BRIEFING.md`, `progress.md`, `plan.md`, `SCOPE.md`) and launch recurring heartbeat timer.
2. **Exploration Phase**: Spawn 3 `teamwork_preview_explorer` agents to examine `sovereign_gate.py`, `agent_smith.py`, `tool_maker.py`, and existing tests/test structure. Formulate exact refactoring and test creation strategy.
3. **Implementation Phase**: Spawn 1 `teamwork_preview_worker` armed with mandatory integrity warning to implement code refactorings and unit tests.
4. **Review Phase**: Spawn 2 `teamwork_preview_reviewer` agents to verify implementation correctness, completeness, robustness, and test coverage.
5. **Challenge Phase**: Spawn 2 `teamwork_preview_challenger` agents to empirically test path resolution, shell blocking, template loading, and system prompt behavior across different CWDs.
6. **Audit Phase**: Spawn 1 `teamwork_preview_auditor` agent to run forensic integrity checks.
7. **Gate Evaluation**: If all criteria pass, send final handoff message to parent orchestrator (`9238f052-3c80-46fc-a4ee-76dc33986dac`). If any check fails (or audit vetoes), iterate back to step 2 with full feedback.
