# Detailed Analysis & Handoff Report: AgentK Test Infrastructure & Tooling Exploration

**Agent ID**: `explorer_m1_2`  
**Working Directory**: `/Users/ricardo/AgentK/agents/.agents/explorer_m1_2`  
**Date**: 2026-07-25  
**Target File**: `/Users/ricardo/AgentK/agents/.agents/explorer_m1_2/analysis.md`  

---

## Executive Summary

This report presents a thorough investigation of the existing test framework, tool ecosystem, test utilities, and mock patterns within the AgentK system (`/Users/ricardo/AgentK/`). It outlines concrete findings and recommendations for structuring the upcoming End-to-End (E2E) test suite under `/Users/ricardo/AgentK/tests/e2e/` (Milestone 4).

---

## 1. Current Test Framework Setup & Runner Analysis

### Findings & Observations
- **Test Framework**: Existing unit tests are written using Python's standard `unittest` library (`import unittest`).
- **Existing Test Files**:
  - `tests/agents/test_software_engineer.py`
  - `tests/agents/test_web_researcher.py`
  - `tests/tools/test_delete_file.py`
  - `tests/tools/test_fetch_web_page_raw_html.py`
  - `tests/tools/test_overwrite_file.py`
  - `tests/tools/test_read_file.py`
  - `tests/tools/test_request_human_input.py`
- **Execution & Imports**:
  - Tests inherit from `unittest.TestCase` and implement an `if __name__ == '__main__': unittest.main()` entry point.
  - Directory structure: `tests/__init__.py` exists, but subdirectories `tests/agents/` and `tests/tools/` do NOT contain `__init__.py` files.
  - Root directories `agents/` and `tools/` do NOT contain `__init__.py` files.
- **Import Resolution Collision**:
  - When running `pytest tests/` or `python3 -m unittest discover`, tests in `tests/tools/` fail with:
    `ImportError: cannot import name 'delete_file' from 'tools' (/Users/ricardo/.local/lib/python3.13/site-packages/tools/__init__.py)`
  - **Cause**: Python resolves `from tools import <tool_name>` to the third-party `tools` package installed in global `site-packages` rather than the local `/Users/ricardo/AgentK/tools` directory because `tools/` lacks an `__init__.py` and `PYTHONPATH` does not prioritize the local project directory.
- **Dependency Issues**:
  - Running agent tests under standard environment yields `ModuleNotFoundError: No module named 'langchain_openai'` via `config.py:2`.

### Current Test Execution Commands
- **Individual Tool Test**: `PYTHONPATH=/Users/ricardo/AgentK python3 tests/tools/test_read_file.py`
- **Unittest Discovery (Subdirectory-scoped)**: `PYTHONPATH=/Users/ricardo/AgentK python3 -m unittest discover -s tests/tools`
- **Pytest Runner**: `PYTHONPATH=/Users/ricardo/AgentK python3 -m pytest tests/`

---

## 2. Available Tools & Agent Tool Interactivity

### Available Tools Inventory (`/Users/ricardo/AgentK/tools/`)
The system features 12 dynamic tool modules:

| Tool Module | Signature / Function | Summary & Mechanics |
|---|---|---|
| `assign_agent_to_task.py` | `@tool assign_agent_to_task(agent_name: str, task: str)` | Dynamically loads `agents/{agent_name}.py` via `utils.load_module()`, invokes agent with `task`, enforces recursion depth cap (`MAX_DEPTH = 3`). |
| `delete_file.py` | `@tool delete_file(file_path: str)` | Deletes a file using `os.remove(file_path)`. |
| `duck_duck_go_news_search.py` | `@tool duck_duck_go_news_search(query: str)` | Queries DuckDuckGo News search for recent items. |
| `duck_duck_go_web_search.py` | `@tool duck_duck_go_web_search(query: str)` | Queries DuckDuckGo Web search. |
| `fetch_web_page_content.py` | `@tool fetch_web_page_content(url: str)` | Renders and parses page content using `SeleniumURLLoader` (headless Chrome). |
| `fetch_web_page_raw_html.py` | `@tool fetch_web_page_raw_html(url: str)` | Downloads raw HTML string from target URL. |
| `list_available_agents.py` | `@tool list_available_agents()` | Invokes `utils.all_agents()` to return dictionary of available agents and docstrings. |
| `overwrite_file.py` | `@tool overwrite_file(file_path: str, content: str)` | Replaces existing file contents with new string content. |
| `read_file.py` | `@tool read_file(file_path: str)` | Reads and returns full file content string. |
| `request_human_input.py` | `@tool request_human_input(prompt: str)` | Prompts user interactively via CLI `input(prompt)`. |
| `run_shell_command.py` | `@tool run_shell_command(command: str)` | Executes shell command using `subprocess.run(command, shell=True, capture_output=True, text=True)`. |
| `write_to_file.py` | `@tool write_to_file(file_path: str, content: str)` | Creates and writes new file content. |

### How Tools Interact with Agents
1. **LangChain Tool Decoration**: All tools are decorated with `@tool` from `langchain_core.tools`.
2. **Model Tool Binding**: Agents bind tools to the LLM model using `config.default_langchain_model.bind_tools(tools)`.
3. **LangGraph Execution Loop**:
   - `reasoning` node invokes the model with `MessagesState`.
   - `check_for_tool_calls` conditional edge routes to `ToolNode(tools)` if `last_message.tool_calls` is present.
   - `acting` node executes the tool call and routes back to `reasoning`.
4. **Dynamic Loading (`utils.py`)**:
   - `utils.all_tool_functions()` uses `load_module("tools/<tool>.py")` with `gensym()` to dynamically import tools without name collisions.
5. **Control Plane Interception (`agents/sovereign_gate.py`)**:
   - `sovereign_gate.py` defines policies (`get_sovereign_policies()`) that inspect `ToolCall` requests.
   - Blocks write/delete operations targeting `PROTECTED_PATHS` (`agent_kernel.py`, `sdk_bridge.py`, `sovereign_gate.py`, `self_heal.sh`, `requirements.txt`, `assign_agent_to_task.py`, `.git`).
   - Intercepts shell execution commands (`run_command`, `run_shell_command`) and agent creation for user approval.

---

## 3. Existing Test Utilities, Fixtures & Mock Patterns

1. **Lifecycle Fixtures (`setUp` / `tearDown`)**:
   - Tool tests (e.g. `test_delete_file.py`, `test_overwrite_file.py`, `test_read_file.py`) create local dummy files (`test_file.txt`) in `setUp()` and clean them up in `tearDown()`.
2. **Mocking External I/O**:
   - `unittest.mock.patch` is used in `test_request_human_input.py` to mock `builtins.input`:
     `@patch('builtins.input', return_value='test input')`
3. **Agent Callable Verification**:
   - `test_software_engineer.py` and `test_web_researcher.py` perform basic sanity checks checking `self.assertTrue(callable(agent_function))`. `PROJECT.md` identifies this as a known limitation to be enhanced in M2/M4.
4. **System Self-Diagnostics (`utils.py`)**:
   - `utils.list_broken_tools()` and `utils.list_broken_agents()` attempt module loading and return detailed tracebacks for syntax or import failures.
5. **Adversarial Security Test Harness (`stress_test_sovereign.py`)**:
   - Standalone chaos-injection script testing 10 attack surfaces (file overwrites, shell escapes, rogue agent creation, malicious tool creation, dependency injection, git history deletion, credential hijacking, recursive spawner fork bombs, cron persistence, gate bypasses).

---

## 4. Recommendations for E2E Test Suite (`tests/e2e/`)

### Proposed Directory & Architecture Layout
```
tests/
├── __init__.py
├── agents/
│   ├── __init__.py
│   ├── test_software_engineer.py
│   └── test_web_researcher.py
├── tools/
│   ├── __init__.py
│   ├── test_delete_file.py
│   └── ...
└── e2e/
    ├── __init__.py
    ├── run_e2e_tests.py           # Core E2E runner CLI script
    ├── conftest.py                # Pytest fixtures, isolated workspace setup
    ├── tier1_basic/               # Tier 1: Core Tool & Single Agent Execution
    │   ├── test_tool_invocations.py
    │   └── test_single_agent.py
    ├── tier2_multi_agent/         # Tier 2: Hermes Orchestration & Delegation
    │   └── test_hermes_delegation.py
    ├── tier3_self_evolution/      # Tier 3: AgentSmith & ToolMaker Dynamic Generation
    │   ├── test_agent_creation.py
    │   └── test_tool_creation.py
    ├── tier4_sdk_bridge/          # Tier 4: Antigravity SDK & Control Plane Integration
    │   └── test_sdk_bridge.py
    └── tier5_adversarial/         # Tier 5: White-Box Sovereign Gate Hardening
        └── test_sovereign_adversarial.py
```

### Key Recommendations for `run_e2e_tests.py` & E2E Suite Design

1. **Python Path Isolation & Namespace Package Fix**:
   - `run_e2e_tests.py` must explicitly insert project root `Path(__file__).resolve().parents[2]` at index `0` of `sys.path`.
   - Adding `__init__.py` files to `agents/`, `tools/`, `tests/agents/`, `tests/tools/`, and `tests/e2e/` will prevent system `site-packages` collisions.
2. **Sandbox Workspace Fixtures**:
   - Create a dedicated temporary directory (`tempfile.TemporaryDirectory()`) per test run for file operations (`write_to_file`, `overwrite_file`, `delete_file`).
   - Isolate SQLite checkpoint DB by setting test-specific checkpoint connection (e.g. `:memory:` or `test_checkpoints.sqlite`) to prevent polluting production `checkpoints.sqlite`.
3. **Deterministic LLM Mocking / Recording**:
   - Provide a `--mock-llm` command-line flag in `run_e2e_tests.py` using `langchain_community.chat_models.fake.FakeMessagesListChatModel` or `unittest.mock.patch("config.default_langchain_model")`.
   - Allows deterministic, zero-cost, offline execution of multi-turn agent conversations during CI runs.
4. **Structured Tiered Test Execution & Reporting**:
   - CLI options: `python tests/e2e/run_e2e_tests.py --tier [1|2|3|4|5|all] --report-json report.json`.
   - Output structured test execution summary adhering to Forensic Integrity Audit criteria (verifying genuine execution without hardcoded facades).
5. **Security Gate Enforcement**:
   - Verify that policy enforcement via `sovereign_gate.py` remains active during E2E runs to catch unauthorized modifications to protected files.

---

## 5-Component Handoff Report

### 1. Observation
- **Root Directory Files**: `PROJECT.md`, `README.md`, `agent_kernel.py`, `config.py`, `utils.py`, `stress_test_sovereign.py`, `requirements.txt`.
- **Existing Test Files**: 7 files under `tests/agents/` (2 files) and `tests/tools/` (5 files). All import `unittest`.
- **Package Init Files**: `tests/__init__.py` is present. No `__init__.py` in `tools/`, `agents/`, `tests/agents/`, or `tests/tools/`.
- **Command Executions & Errors**:
  - `python3 -m unittest discover -s tests -p "test_*.py"` -> `Ran 0 tests in 0.000s (NO TESTS RAN)` because tests are in subdirectories.
  - `python3 -m pytest tests/` -> `7 errors during collection`.
    - Error in agent tests: `ModuleNotFoundError: No module named 'langchain_openai'` (via `config.py:2`).
    - Error in tool tests: `ImportError: cannot import name 'delete_file' from 'tools' (/Users/ricardo/.local/lib/python3.13/site-packages/tools/__init__.py)`.
- **Tools Inventory**: 12 python files in `tools/`, all decorated with `@tool`.

### 2. Logic Chain
- Step 1: Observing `Ran 0 tests` with default unittest discovery indicates that subdirectories `tests/agents` and `tests/tools` were skipped because they lack `__init__.py` files and default `-s tests` search patterns did not recurse into un-packaged directories.
- Step 2: Observing `ImportError` when importing `tools` in pytest reveals that Python matched `/Users/ricardo/.local/lib/python3.13/site-packages/tools/__init__.py` instead of `./tools/` because `./tools/` has no `__init__.py` and project root was not prepended to `sys.path`.
- Step 3: Examining `utils.py` showed dynamic loading via `importlib.util.spec_from_file_location`, which bypasses static package resolution for runtime agent loading but does not fix test module import paths.
- Step 4: Examining `agents/software_engineer.py` and `agents/hermes.py` confirmed that agents use standard LangGraph `StateGraph` workflows with `ToolNode`, invoking tools via `.bind_tools()`.
- Step 5: Synthesizing these observations yields the required fixes for test infrastructure: explicit `PYTHONPATH` handling, package `__init__.py` creation, sandbox workspace isolation, and tier-based test execution structure.

### 3. Caveats
- Did not execute live LLM calls requiring `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` to avoid unintended API consumption.
- Did not modify any repository source files or test files (adhering strictly to read-only investigation constraint).

### 4. Conclusion
AgentK's current test suite relies on standard `unittest`, but requires python path adjustments and package structure fixes to execute cleanly via pytest or unittest discovery. The 12 tools under `tools/` and 5 agents under `agents/` interact via LangGraph state graphs and dynamic module loading. The new E2E test runner (`tests/e2e/run_e2e_tests.py`) should structure tests into Tiers 1-5, enforce workspace isolation via temporary directories, support offline deterministic LLM mocks, and integrate sovereign gate security policies.

### 5. Verification Method
1. **Inspect Report**: Read `/Users/ricardo/AgentK/agents/.agents/explorer_m1_2/analysis.md`.
2. **Verify Import Conflict**:
   Run `PYTHONPATH=. python3 -m pytest tests/` vs `python3 -m pytest tests/` to verify the module import behavior.
3. **Verify Tool List**:
   Run `PYTHONPATH=/Users/ricardo/AgentK python3 -c "import utils; print(utils.list_tools())"` to verify all 12 tools are detected.
