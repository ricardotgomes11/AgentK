## 2026-07-25T17:09:20Z
<USER_REQUEST>
You are Worker 1 for Milestone 2: Agent Interfaces & Quality Fixes.
Your working directory is /Users/ricardo/AgentK/agents/.agents/worker_m2_1. Create your folder if it doesn't exist, and write progress.md and handoff.md in it.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope & Tasks to Implement:

1. **Return Type Annotations & Interfaces**:
   - Refactor agent entry point signatures in /Users/ricardo/AgentK/agents/ (agent_smith.py, software_engineer.py, tool_maker.py, web_researcher.py) to accurately annotate return types (`-> dict[str, Any]` for LangGraph state dict returns).
   - Ensure `from typing import Any, Literal` is imported in all 4 files.
   - Annotate internal graph node helper functions `reasoning(state: MessagesState) -> dict[str, Any]:` in all 4 files.
   - Ensure clean dict state returns with `"messages"` list.

2. **Prompt & Syntax Quality Fixes**:
   - /Users/ricardo/AgentK/agents/web_researcher.py: Remove unclosed standalone triple backticks `` ``` `` on line 12 in system prompt.
   - /Users/ricardo/AgentK/agents/tool_maker.py: Fix typos ("succintly" -> "succinctly", "asccii" -> "ASCII", "stands kernel" -> "stands for kernel", "message the user" -> "message to the user", "eg." -> "e.g.,").
   - /Users/ricardo/AgentK/agents/agent_smith.py: Fix "stands kernel" -> "stands for kernel", "message the user" -> "message to the user".
   - /Users/ricardo/AgentK/agents/hermes.py: Fix "stands kernel" -> "stands for kernel", duplicate step number 4. -> 5., "optimise" -> "optimize", "activities agents" -> "activities of agents".
   - /Users/ricardo/AgentK/agents/sdk_bridge.py: Fix "optimise" -> "optimize".

3. **Unit Test Suite Implementation**:
   - /Users/ricardo/AgentK/tests/agents/test_software_engineer.py: Upgrade beyond callable() to test callable & compiled graph, tool bindings (all 7 tools: write_to_file, overwrite_file, delete_file, read_file, run_shell_command, assign_agent_to_task, list_available_agents), system prompt content, check_for_tool_calls routing ("tools" vs "__end__"), reasoning node mock, and end-to-end sandboxed file execution in a tempfile.
   - /Users/ricardo/AgentK/tests/agents/test_tool_maker.py: Retain existing platform info & prompt builder tests, add tests for dynamic tool loading, check_for_tool_calls state routing, reasoning node, AST syntax parsing of synthesized tool & unittest code, and sandboxed end-to-end tool creation flow.
   - /Users/ricardo/AgentK/tests/agents/test_web_researcher.py: Upgrade beyond callable() to test search tool bindings (duck_duck_go_web_search, fetch_web_page_content), system prompt content, check_for_tool_calls routing, offline DuckDuckGo search mock, offline Web Page fetcher mock, and full multi-step offline ReAct loop without network access.

Verification:
Run unit tests for all target agent files using `pytest` or `python3 -m unittest discover tests/agents`. Verify that all tests pass cleanly.

Document all modified files, test command outputs, and pass results in your `/Users/ricardo/AgentK/agents/.agents/worker_m2_1/handoff.md` and report back to parent sub-orchestrator.
</USER_REQUEST>
