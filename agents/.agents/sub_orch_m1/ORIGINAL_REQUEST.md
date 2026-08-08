# Original User Request

## 2026-07-25T16:46:10Z

You are the Sub-orchestrator for Milestone 1: Control Plane & Path Portability. Your working directory is /Users/ricardo/AgentK/agents/.agents/sub_orch_m1.
Create your working directory state files (BRIEFING.md, progress.md, plan.md, SCOPE.md).

Scope of Milestone 1:
1. Refactor /Users/ricardo/AgentK/agents/sovereign_gate.py: Replace hardcoded local user absolute paths (/Users/ricardo/AgentK/...) in PROTECTED_PATHS and shell checks with dynamic project root path resolution (e.g. Path(__file__).resolve().parents[1]).
2. Refactor /Users/ricardo/AgentK/agents/agent_smith.py: Fix relative path loading (open("agents/web_researcher.py") and open("tests/agents/test_web_researcher.py")) so template reading resolves paths relative to __file__, preventing CWD dependency import crashes.
3. Update /Users/ricardo/AgentK/agents/tool_maker.py: Update system prompt to be OS-agnostic / configurable instead of hardcoded Debian 11.
4. Implement unit tests under /Users/ricardo/AgentK/tests/agents/: Write test_sovereign_gate.py and test_agent_smith.py to thoroughly test path resolution, policy hooks, shell blocking regex, and template loading.

Procedure:
Run the Explorer -> Worker -> Reviewer -> Challenger -> Forensic Auditor iteration loop for Milestone 1.
Worker MUST be armed with the MANDATORY INTEGRITY WARNING (DO NOT CHEAT).
Forensic Auditor is MANDATORY — failure or integrity violation is a BINARY VETO.
Do NOT write code directly — delegate implementation to workers!
Send a message to the parent orchestrator when Milestone 1 passes all gate criteria.
