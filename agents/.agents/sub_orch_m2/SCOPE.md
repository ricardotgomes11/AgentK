# Scope: Milestone 2 — Agent Interfaces & Quality Fixes

## Architecture & Overview
Milestone 2 targets refactoring agent entry points, fixing prompt/syntax flaws, and building/upgrading comprehensive unit tests for `agent_smith.py`, `software_engineer.py`, `tool_maker.py`, and `web_researcher.py`.

## Scope Items
1. **Return Type Annotations & Interfaces**:
   - Refactor agent entry point signatures in `/Users/ricardo/AgentK/agents/` (`agent_smith.py`, `software_engineer.py`, `tool_maker.py`, `web_researcher.py`) to accurately annotate return types (`-> dict[str, Any]` for LangGraph state dict returns, or `str` when helper wrapper is called).
   - Ensure clean dict state returns with `"messages"` list.
2. **Prompt & Syntax Quality Fixes**:
   - `/Users/ricardo/AgentK/agents/web_researcher.py`: Fix unclosed triple backticks in system prompt string.
   - `/Users/ricardo/AgentK/agents/tool_maker.py`: Fix typos ("succintly") and improve system prompt clarity.
3. **Unit Test Suite Implementation**:
   - `/Users/ricardo/AgentK/tests/agents/test_software_engineer.py`: Upgrade beyond `callable()` to test graph state, tool bindings, and file operation sandbox.
   - `/Users/ricardo/AgentK/tests/agents/test_tool_maker.py`: Implement test suite for tool synthesis graph, prompt builder, and unittest generation.
   - `/Users/ricardo/AgentK/tests/agents/test_web_researcher.py`: Upgrade beyond `callable()` to test graph state, search tool bindings, and DDG / web fetcher offline mocks.

## Milestones / Work Items
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 2.1 | Exploration & Fix Strategy | Analyze code, identify type annotations, unclosed backticks, typos, and test gaps | None | IN_PROGRESS |
| 2.2 | Code & Prompt Implementation | Apply return type annotations, prompt fixes, and unit test suites | 2.1 | PLANNED |
| 2.3 | Review & Verification | Code review and adversarial verification | 2.2 | PLANNED |
| 2.4 | Forensic Audit | Forensic integrity audit verification | 2.3 | PLANNED |

## Interface Contracts
- `run_agent_smith`, `run_software_engineer`, `run_tool_maker`, `run_web_researcher` entry point signatures must have clear, accurate return type annotations (`-> dict[str, Any]` or `-> str` as appropriate).
- State returned must contain `"messages"` key with list of messages.
