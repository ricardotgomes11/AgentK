# AgentK Testing, Build, Execution, and Environment Analysis Report

**Author**: Explorer 2  
**Date**: 2026-07-25  
**Target Path**: `/Users/ricardo/AgentK/agents/`  
**Working Directory**: `/Users/ricardo/AgentK/agents/.agents/teamwork_preview_explorer_2`

---

## Executive Summary

AgentK is a self-evolving AGI system built on top of **LangGraph**, **LangChain**, and the **google-antigravity** SDK. A comprehensive investigation of `/Users/ricardo/AgentK/` and `/Users/ricardo/AgentK/agents/` reveals that while the project includes basic Docker containerization and a small set of initial `unittest` files, the overall test infrastructure is fragmented and incomplete.

Key findings:
1. **Existing Tests**: Only 2 out of the 7 core agent modules (`software_engineer.py` and `web_researcher.py`) have smoke tests, and both tests merely check `callable()`. Five core modules (`agent_smith.py`, `hermes.py`, `sdk_bridge.py`, `sovereign_gate.py`, and `tool_maker.py`) have **no unit tests at all**.
2. **Environment & Dependency Gaps**: Dependencies are defined in `requirements.txt` (11 packages) and `Dockerfile`, but the host system Python environment (`/usr/local/bin/python3`) lacks several mandatory packages (e.g., `langchain-openai`, `langchain-anthropic`, `langgraph-checkpoint-sqlite`, `google-antigravity`). Running tests directly via system python fails with `ModuleNotFoundError`.
3. **Import Side-Effects & Path Sensitivity**:
   - `agents/agent_smith.py` performs top-level file `open()` calls on relative paths (`agents/web_researcher.py` and `tests/agents/test_web_researcher.py`), causing `FileNotFoundError` if imported outside the project root CWD.
   - `agents/hermes.py` executes tool invocation `list_available_agents.invoke({})` at module load time, triggering dynamic module scanning of all agents upon import.
   - `agents/hermes.py` contains an interactive blocking CLI loop (`input("> ")`) in node execution.
4. **Missing Configuration Standards**: No `pytest.ini`, `pyproject.toml`, or `setup.py` exist in the repository. Standard unittest test discovery (`python3 -m unittest discover -s tests`) fails unless explicit pattern flags (`-p "test_*.py"`) and `PYTHONPATH=.` are supplied.

---

## 1. Existing Tests, Configurations, and Build Files

### 1.1 File Discovery Summary

| Category | File Path | Description / Purpose |
| :--- | :--- | :--- |
| **Dependencies** | `/Users/ricardo/AgentK/requirements.txt` | Lists 11 Python dependencies: `langgraph==0.2.0`, `langchain-community==0.2.11`, `langgraph-checkpoint==1.0.1`, `langchain-openai`, `langchain-anthropic`, `langgraph-checkpoint-sqlite`, `selenium`, `unstructured`, `duckduckgo-search`, `python-dotenv`, `google-antigravity`. |
| **System Packages** | `/Users/ricardo/AgentK/apt-packages-list.txt` | Lists Linux apt packages: `wget`, `curl`, `git`, `chromium-driver`, `ca-certificates`, `cmake`, `libclang-dev`. |
| **Docker Build** | `/Users/ricardo/AgentK/Dockerfile` | Debian Bullseye container definition building Rust, apt packages, pip requirements, and running `ENTRYPOINT ["python", "agent_kernel.py"]`. |
| **Docker Compose** | `/Users/ricardo/AgentK/docker-compose.yml` | Service `agentk` mounting `./:/app` with `.env` file support. |
| **Launcher** | `/Users/ricardo/AgentK/agentk` | Shell script launcher: `docker compose run --rm agentk "$@"`. |
| **Existing Agent Tests** | `/Users/ricardo/AgentK/tests/agents/test_software_engineer.py` | Smoke test verifying `callable(software_engineer)`. |
| **Existing Agent Tests** | `/Users/ricardo/AgentK/tests/agents/test_web_researcher.py` | Smoke test verifying `callable(web_researcher)`. |
| **Existing Tool Tests** | `/Users/ricardo/AgentK/tests/tools/test_delete_file.py` | Unit test for `delete_file` tool. |
| **Existing Tool Tests** | `/Users/ricardo/AgentK/tests/tools/test_fetch_web_page_raw_html.py` | Unit test for `fetch_web_page_raw_html` tool. |
| **Existing Tool Tests** | `/Users/ricardo/AgentK/tests/tools/test_overwrite_file.py` | Unit test for `overwrite_file` tool. |
| **Existing Tool Tests** | `/Users/ricardo/AgentK/tests/tools/test_read_file.py` | Unit test for `read_file` tool. |
| **Existing Tool Tests** | `/Users/ricardo/AgentK/tests/tools/test_request_human_input.py` | Unit test for `request_human_input` tool. |
| **Missing Configurations** | `pyproject.toml`, `setup.py`, `pytest.ini`, `tox.ini` | **None present**. |

### 1.2 Inspection of Existing Agent Tests

1. `tests/agents/test_software_engineer.py`:
   ```python
   import unittest
   from agents.software_engineer import software_engineer

   class TestSoftwareEngineer(unittest.TestCase):
       def test_software_engineer(self):
           self.assertTrue(callable(software_engineer))

   if __name__ == '__main__':
       unittest.main()
   ```

2. `tests/agents/test_web_researcher.py`:
   ```python
   import unittest
   from agents.web_researcher import web_researcher

   class TestWebResearcher(unittest.TestCase):
       def test_web_researcher(self):
           self.assertTrue(callable(web_researcher))

   if __name__ == '__main__':
       unittest.main()
   ```

Both existing agent tests are minimal smoke tests that only verify function callability without invoking graph execution or verifying tool interactions.

---

## 2. Execution, Import, and Verification Mechanics

### 2.1 Module Execution Vectors

Python modules in `/Users/ricardo/AgentK/agents/` are intended to be executed in three ways:

1. **Docker Container Execution (Production Vector)**:
   - Command: `./agentk` (executes `docker compose run --rm agentk`).
   - Entrypoint: `python agent_kernel.py` inside the container.
   - `agent_kernel.py` generates a UUID and invokes `hermes.hermes(uuid)`.

2. **SDK Bridge Dispatch (`agents/sdk_bridge.py`)**:
   - `dispatch_agent(agent_name: str, task: str) -> str`
   - Dynamically loads `agents/{agent_name}.py` via `utils.load_module()`, invokes the agent function with `task=task`, and unregisters the module from `sys.modules`.

3. **Direct Agent Invocation**:
   - Each agent exposes a main function accepting a string `task` (or `uuid` for `hermes`):
     - `agent_smith(task: str)`
     - `hermes(uuid: str)`
     - `software_engineer(task: str)`
     - `tool_maker(task: str)`
     - `web_researcher(task: str)`

### 2.2 Import Dependencies & Side-Effects

Modules in `agents/` rely on root-level package imports (`import config`, `import utils`, `from tools.X import X`). Therefore:
- The project root `/Users/ricardo/AgentK` **must** be present on `sys.path` (or set via `PYTHONPATH=/Users/ricardo/AgentK`).

#### Side-Effects at Import Time:
1. **`agents/agent_smith.py`**:
   - Lines 12–16:
     ```python
     example_agent = "web_researcher"
     with open(f"agents/{example_agent}.py", 'r') as file:
         agent_code = file.read()
     with open(f"tests/agents/test_{example_agent}.py", 'r') as file:
         agent_test_code = file.read()
     ```
   - **Risk**: Top-level code executes `open()` with relative paths. If python is run from any directory other than `/Users/ricardo/AgentK`, importing `agent_smith` raises `FileNotFoundError`.

2. **`agents/hermes.py`**:
   - Line 43:
     ```python
     system_prompt = f"""... {list_available_agents.invoke({})}"""
     ```
   - **Risk**: Calling `list_available_agents.invoke({})` during system prompt construction executes `utils.all_agents()`, which dynamically loads all agent files in `agents/` at import time.

3. **`agents/sovereign_gate.py`**:
   - Imports `google.antigravity.hooks` and `google.antigravity.types`. Hardcodes absolute paths to `/Users/ricardo/AgentK/...`. Requires `google-antigravity` SDK.

### 2.3 Verification Commands

To run tests in this environment:
- Direct test file execution:
  ```bash
  PYTHONPATH=/Users/ricardo/AgentK python3 -m unittest tests/agents/test_software_engineer.py
  ```
- Full agent test suite run:
  ```bash
  PYTHONPATH=/Users/ricardo/AgentK python3 -m unittest discover -s tests/agents -p "test_*.py"
  ```
- Pytest execution (when environment dependencies are satisfied):
  ```bash
  PYTHONPATH=/Users/ricardo/AgentK /Users/ricardo/.local/bin/pytest tests/
  ```

---

## 3. Target Module Analysis & Infrastructure Requirements

### Summary Matrix of Target Modules

| Target Module | Function / Entry Point | Current Test File | Import Side-Effects | Primary Dependencies | Test Infrastructure Needed |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`agent_smith.py`** | `agent_smith(task)` | None | Reads relative agent/test files | `config`, `utils`, `langgraph`, `langchain` | CWD path mocking, LLM mocking, file creation sandbox |
| **`hermes.py`** | `hermes(uuid)` | None | Invokes tool `list_available_agents` at import | `utils`, `config`, `tools`, SQLite saver | Stdin (`input()`) mocking, SQLite checkpointer sandbox, LLM mocking |
| **`sdk_bridge.py`** | `dispatch_agent()`, inventory functions | None | Modifies `sys.path` dynamically | `utils`, `sys`, `sqlite3`, `traceback` | Mock agent loader, test `sys.modules` cleanup & error handling |
| **`software_engineer.py`** | `software_engineer(task)` | `test_software_engineer.py` (smoke) | Compiles LangGraph workflow | `config`, file/shell tools, `langgraph` | Temporary directory sandbox (`tmp_path`), tool call mocking |
| **`sovereign_gate.py`** | `get_sovereign_policies()` | None | None | `google.antigravity` | Policy rule unit tests, path predicate tests, stdin approval mocking |
| **`tool_maker.py`** | `tool_maker(task)` | None | Compiles LangGraph workflow | `utils`, `config`, `langgraph` | Tool file generation sandbox, test execution runner mock |
| **`web_researcher.py`** | `web_researcher(task)` | `test_web_researcher.py` (smoke) | Compiles LangGraph workflow | `config`, DDG/fetch tools | Web search & HTTP response mocking (essential for CODE_ONLY mode) |

---

### Detailed Breakdown per Target Module

#### 1. `agent_smith.py`
- **Purpose**: Creates new ReAct agents and their corresponding smoke tests.
- **Key Lines**:
  - L12–16: Hardcoded relative file reads (`agents/web_researcher.py`, `tests/agents/test_web_researcher.py`).
  - L76: `config.default_langchain_model.bind_tools(tools)`
  - L109: `def agent_smith(task: str) -> str:`
- **Infrastructure Needed**:
  - `test_agent_smith.py`: Unit test verifying `agent_smith` interface and export.
  - Safe path loader fixture to mock top-level `open()` calls when CWD is not root.
  - Mock `write_to_file` tool call to capture and inspect generated agent python code and test code without writing to production `agents/` directory.

#### 2. `hermes.py`
- **Purpose**: Top-level interactive orchestrator agent.
- **Key Lines**:
  - L43: Formats system prompt by calling `list_available_agents.invoke({})` at module load time.
  - L58–59: `while not human_input.strip(): human_input = input("> ")` (blocks waiting for stdin).
  - L110: `graph = workflow.compile(checkpointer=utils.checkpointer)` (writes to `checkpoints.sqlite`).
- **Infrastructure Needed**:
  - `test_hermes.py`: Unit test suite.
  - `monkeypatch` / `unittest.mock.patch('builtins.input')` fixture to feed mock user input.
  - Temporary isolated SQLite database fixture for `checkpointer` to avoid corrupting `checkpoints.sqlite`.
  - LLM response mock for task routing and tool call logic.

#### 3. `sdk_bridge.py`
- **Purpose**: Exposes AgentK's agent inventory and dispatching capabilities to google-antigravity SDK.
- **Key Lines**:
  - L29: `get_agent_inventory()`
  - L46: `get_tool_inventory()`
  - L59: `get_system_prompt()`
  - L104: `dispatch_agent(agent_name: str, task: str) -> str`
- **Infrastructure Needed**:
  - `test_sdk_bridge.py`: Unit test suite verifying inventory output formatting, system prompt composition, and agent dispatch behavior.
  - Mock module loader to verify `sys.modules` registration and cleanup after `dispatch_agent()` completes.

#### 4. `software_engineer.py`
- **Purpose**: Creates, modifies, and deletes code, executes shell commands.
- **Key Lines**:
  - L22–30: Tools bound (`write_to_file`, `overwrite_file`, `delete_file`, `read_file`, `run_shell_command`, `assign_agent_to_task`, `list_available_agents`).
  - L69: `def software_engineer(task: str) -> str:`
- **Infrastructure Needed**:
  - `test_software_engineer.py`: Expand existing callability test into full unit test suite.
  - Filesystem Sandbox: Execute file operations within a isolated temporary working directory (`pytest` `tmp_path` or `tempfile.TemporaryDirectory`).
  - Command Execution Interception: Mock `run_shell_command` to prevent unintended host command execution during unit test runs.

#### 5. `sovereign_gate.py`
- **Purpose**: Access policy engine and security gate protecting kernel files and git repository integrity.
- **Key Lines**:
  - L14–21: `PROTECTED_PATHS` set (`agent_kernel.py`, `sdk_bridge.py`, `sovereign_gate.py`, `self_heal.sh`, `requirements.txt`, `assign_agent_to_task.py`).
  - L24: `is_protected_path(path)`
  - L36: `_is_agent_or_tool_write(tc)`
  - L47: `_deny_protected_writes(tc)`
  - L58: `_deny_dangerous_commands(tc)`
  - L74: `console_approval_handler(tc)`
  - L86: `get_sovereign_policies()`
- **Infrastructure Needed**:
  - `test_sovereign_gate.py`: High-priority security test suite.
  - Unit tests for `is_protected_path()` asserting TRUE for protected paths and `.git/`, FALSE for normal files.
  - Unit tests for `_deny_dangerous_commands()` testing string patterns containing `rm`, `mv`, `>`, `chmod`, `sed` against protected filenames.
  - Unit tests for `console_approval_handler()` mocking user stdin response (`y` vs `n`/EOF).

#### 6. `tool_maker.py`
- **Purpose**: Generates new LangChain tools and unit tests, verifying test pass status via shell command.
- **Key Lines**:
  - L40: Prompt instructs running `python -m unittest path_to_test_file`.
  - L139: `def tool_maker(task: str) -> str:`
- **Infrastructure Needed**:
  - `test_tool_maker.py`: Unit test verifying `tool_maker` graph definition and interface.
  - Mock environment for tool test runner execution.
  - Tool generation directory sandbox to isolate created tool files during testing.

#### 7. `web_researcher.py`
- **Purpose**: Performs web search and page content retrieval.
- **Key Lines**:
  - L18: Tools bound (`duck_duck_go_web_search`, `fetch_web_page_content`).
  - L57: `def web_researcher(task: str) -> str:`
- **Infrastructure Needed**:
  - `test_web_researcher.py`: Expand existing callability test.
  - Web Search / HTTP Mocking: Mock `duck_duck_go_web_search` and `fetch_web_page_content` tool outputs. Mandatory for deterministic offline testing and operation in CODE_ONLY mode.

---

## 4. Recommendations for Test Infrastructure Roadmap

1. **Environment Standardization**:
   - Create a virtual environment or ensure all dependencies listed in `requirements.txt` are installed in the test execution environment.
   - Add a standard `pyproject.toml` or `pytest.ini` at the root with `pythonpath = ["."]`.

2. **Shared Test Fixtures (`tests/conftest.py`)**:
   - `mock_llm`: A fixture that mocks `config.default_langchain_model.bind_tools()` and `.invoke()`.
   - `temp_workspace`: A fixture providing an isolated temporary directory for file operations.
   - `mock_stdin`: A fixture providing controlled responses to `input()`.
   - `isolated_checkpointer`: A fixture providing an in-memory SQLite checkpointer (`sqlite3.connect(":memory:")`).

3. **Complete Agent Test Suite**:
   - Implement missing test files in `tests/agents/`:
     - `test_agent_smith.py`
     - `test_hermes.py`
     - `test_sdk_bridge.py`
     - `test_sovereign_gate.py`
     - `test_tool_maker.py`
   - Upgrade existing `test_software_engineer.py` and `test_web_researcher.py` with mock-backed graph execution tests.
