# Original User Request

## Initial Request — 2026-07-25T17:05:48-04:00

You are the Sub-orchestrator for Milestone 2: Agent Interfaces & Quality Fixes. Your working directory is /Users/ricardo/AgentK/agents/.agents/sub_orch_m2.
Create your working directory state files (BRIEFING.md, progress.md, plan.md, SCOPE.md).

Scope of Milestone 2:
1. Return Type Annotations & Interfaces:
   - Refactor agent entry point signatures in /Users/ricardo/AgentK/agents/ (agent_smith.py, software_engineer.py, tool_maker.py, web_researcher.py) to accurately annotate return types (-> dict[str, Any] for LangGraph state dict returns, or str when helper wrapper is called).
   - Ensure clean dict state returns with "messages" list.
2. Prompt & Syntax Quality Fixes:
   - /Users/ricardo/AgentK/agents/web_researcher.py: Fix unclosed triple backticks in system prompt string.
   - /Users/ricardo/AgentK/agents/tool_maker.py: Fix typos ("succintly") and system prompt clarity.
3. Unit Test Suite Implementation:
   - /Users/ricardo/AgentK/tests/agents/test_software_engineer.py: Upgrade beyond callable() to test graph state, tool bindings, and file operation sandbox.
   - /Users/ricardo/AgentK/tests/agents/test_tool_maker.py: Implement test suite for tool synthesis graph, prompt builder, and unittest generation.
   - /Users/ricardo/AgentK/tests/agents/test_web_researcher.py: Upgrade beyond callable() to test graph state, search tool bindings, and DDG / web fetcher offline mocks.

Procedure:
Run the Explorer -> Worker -> Reviewer -> Challenger -> Forensic Auditor iteration loop for Milestone 2.
Worker MUST be armed with the MANDATORY INTEGRITY WARNING (DO NOT CHEAT).
Forensic Auditor is MANDATORY — failure or integrity violation is a BINARY VETO.
Do NOT write code directly — delegate implementation to workers!
Send a message to the parent orchestrator when Milestone 2 passes all gate criteria.
