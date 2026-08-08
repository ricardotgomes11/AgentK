# AgentK Core Architecture Analysis & Handoff Report

**Module Scope**: `sovereign_gate.py`, `agent_smith.py`, `hermes.py`, `software_engineer.py`, `tool_maker.py`, `web_researcher.py`, `sdk_bridge.py`, `utils.py`, `config.py`  
**Date**: 2026-07-25  
**Agent**: Explorer (`teamwork_preview_explorer_m1_1`)  
**Working Directory**: `/Users/ricardo/AgentK/agents/.agents/explorer_m1_1`

---

## Executive Summary
This report provides a comprehensive, read-only structural analysis of the core AgentK system modules. It maps exact function signatures, annotated vs runtime return types, system dependencies, environment variable configurations, LLM API client interactions, offline mocking requirements, security boundary policies in `sovereign_gate.py`, and complete input parameter specifications.

---

## 1. Exact Function Signatures & Return Types

Below is the module-by-module breakdown of all entry point functions, internal graph nodes, helpers, and utility functions across the 9 target files.

### 1.1 `agents/sovereign_gate.py`
| Function Signature | Type Annotation Return | Actual Runtime Return | Description |
|---|---|---|---|
| `is_protected_path(path: str \| None)` | `bool` | `bool` | Returns `True` if `path` resolves to a path in `PROTECTED_PATHS` or inside `.git`. |
| `_is_agent_or_tool_write(tc: types.ToolCall)` | `bool` | `bool` | Internal helper checking if tool call target path starts with `agents/` or `tools/`. |
| `_deny_protected_writes(tc: types.ToolCall)` | `bool` | `bool` | Internal helper returning `True` if any file argument matches a protected path. |
| `_deny_dangerous_commands(tc: types.ToolCall)` | `bool` | `bool` | Internal static analyzer blocking dangerous shell commands targeting protected files. |
| `console_approval_handler(tc: types.ToolCall)` | `bool` | `bool` | Interactive terminal prompt handler (`y/N`) for user approval. |
| `get_sovereign_policies()` | `list[policy.Policy]` | `list[google.antigravity.hooks.policy.Policy]` | Assembles and returns the 6-tier security policy list. |

### 1.2 `agents/agent_smith.py`
| Function Signature | Type Annotation Return | Actual Runtime Return | Description |
|---|---|---|---|
| `agent_smith(task: str)` | `str` | `dict[str, Any]` | Primary entry point. Returns compiled LangGraph state dictionary `{"messages": [...]}`. *Note: Type hint is `str`, but `graph.invoke(...)` returns `dict`.* |
| `reasoning(state: MessagesState)` | None | `dict[str, list[BaseMessage]]` | Node function binding tools to model and generating LLM response. |
| `check_for_tool_calls(state: MessagesState)` | `Literal["tools", END]` | `str` (`"tools"` or `"__end__"`) | Conditional edge function routing to `tools` node or ending workflow. |

### 1.3 `agents/hermes.py`
| Function Signature | Type Annotation Return | Actual Runtime Return | Description |
|---|---|---|---|
| `hermes(uuid: str)` | None | `dict[str, Any]` | Primary entry point for orchestrator session. Returns state dict with checkpointer thread ID `uuid`. |
| `feedback_and_wait_on_human_input(state: MessagesState)` | None | `dict[str, list[HumanMessage]]` | Interactively prompts terminal input (`input("> ")`) and appends `HumanMessage`. |
| `check_for_exit(state: MessagesState)` | `Literal["reasoning", END]` | `str` (`"reasoning"` or `"__end__"`) | Checks if user input is `"exit"`. |
| `reasoning(state: MessagesState)` | None | `dict[str, list[BaseMessage]]` | Node function invoking model bound with `list_available_agents` and `assign_agent_to_task`. |
| `check_for_tool_calls(state: MessagesState)` | `Literal["tools", "feedback_and_wait_on_human_input"]` | `str` | Routes to tool node or human feedback node. |

### 1.4 `agents/software_engineer.py`
| Function Signature | Type Annotation Return | Actual Runtime Return | Description |
|---|---|---|---|
| `software_engineer(task: str)` | `str` | `dict[str, Any]` | Primary entry point. Returns state dict `{"messages": [...]}`. *Note: Type hint disparity (`str` vs `dict`).* |
| `reasoning(state: MessagesState)` | None | `dict[str, list[BaseMessage]]` | Node function for code modification reasoning. |
| `check_for_tool_calls(state: MessagesState)` | `Literal["tools", END]` | `str` | Conditional edge function. |

### 1.5 `agents/tool_maker.py`
| Function Signature | Type Annotation Return | Actual Runtime Return | Description |
|---|---|---|---|
| `tool_maker(task: str)` | `str` | `dict[str, Any]` | Primary entry point for tool creation. Returns state dict `{"messages": [...]}`. *Note: Type hint disparity (`str` vs `dict`).* |
| `reasoning(state: MessagesState)` | None | `dict[str, list[BaseMessage]]` | Node function for tool creation reasoning. |
| `check_for_tool_calls(state: MessagesState)` | `Literal["tools", END]` | `str` | Conditional edge function. |

### 1.6 `agents/web_researcher.py`
| Function Signature | Type Annotation Return | Actual Runtime Return | Description |
|---|---|---|---|
| `web_researcher(task: str)` | `str` | `dict[str, Any]` | Primary entry point for web research. Returns state dict `{"messages": [...]}`. *Note: Type hint disparity (`str` vs `dict`).* |
| `reasoning(state: MessagesState)` | None | `dict[str, list[BaseMessage]]` | Node function for research model reasoning. |
| `check_for_tool_calls(state: MessagesState)` | `Literal["tools", END]` | `str` | Conditional edge function. |

### 1.7 `agents/sdk_bridge.py`
| Function Signature | Type Annotation Return | Actual Runtime Return | Description |
|---|---|---|---|
| `get_agent_inventory()` | `str` | `str` | Returns formatted markdown list of non-hermes agents and docstrings. |
| `get_tool_inventory()` | `str` | `str` | Returns formatted markdown list of available tools. |
| `get_system_prompt()` | `str` | `str` | Composes unified system prompt for SDK Agent wrapper. |
| `dispatch_agent(agent_name: str, task: str)` | `str` | `str` | Dynamically imports `agents/{agent_name}.py`, executes it with `task`, extracts and returns string response from `messages[-1].content`. |

### 1.8 `utils.py`
| Function Signature | Type Annotation Return | Actual Runtime Return | Description |
|---|---|---|---|
| `all_tool_functions()` | None | `list[Callable]` | Dynamically imports all tool modules in `tools/` and returns function objects. |
| `list_broken_tools()` | None | `dict[str, list[Any]]` | Scans `tools/`, returns dict mapping failed tool name to `[exception, traceback]`. |
| `list_tools()` | None | `list[str]` | Scans `tools/` directory for `.py` files and returns stem names. |
| `all_agents(exclude=["hermes"])` | None | `dict[str, str \| None]` | Scans `agents/`, dynamically imports, and returns dict of `{agent_name: docstring}`. |
| `list_broken_agents()` | None | `dict[str, list[Any]]` | Scans `agents/`, returns dict of broken agents with error details. |
| `list_agents()` | None | `list[str]` | Scans `agents/` for `.py` files (excluding `__init__.py`). |
| `gensym(length=32, prefix="gensym_")` | None | `str` | Generates a random alphanumeric symbol for dynamic module naming. |
| `load_module(source, module_name=None)` | None | `types.ModuleType` | Loads Python file from `source` path into `sys.modules` under `module_name`. |

### 1.9 `config.py`
Exports top-level variables evaluated at module import:
- `default_model_temperature`: `int` (parsed from `DEFAULT_MODEL_TEMPERATURE`, default `0`)
- `default_model_provider`: `str` (parsed from `DEFAULT_MODEL_PROVIDER`, default `"OPENAI"`)
- `default_model_name`: `str` (parsed from `DEFAULT_MODEL_NAME`, default `"gpt-4o"`)
- `default_langchain_model`: `ChatOpenAI` or `ChatAnthropic` instance.

---

## 2. Dependencies, Environment Variables & Offline Mocking Needs

### 2.1 Package Dependencies
- **Standard Library**: `os`, `sys`, `sqlite3`, `importlib.util`, `string`, `secrets`, `traceback`, `typing`.
- **LangChain Ecosystem**: `langchain_core` (`HumanMessage`, `SystemMessage`), `langchain_openai` (`ChatOpenAI`), `langchain_anthropic` (`ChatAnthropic`).
- **LangGraph Ecosystem**: `langgraph.graph` (`StateGraph`, `MessagesState`, `END`), `langgraph.prebuilt` (`ToolNode`), `langgraph.checkpoint.sqlite` (`SqliteSaver`).
- **Google Antigravity SDK**: `google.antigravity.hooks.policy`, `google.antigravity.types`.

### 2.2 Environment Variables
| Variable Name | Required / Optional | Default Value | Purpose / Impact |
|---|---|---|---|
| `DEFAULT_MODEL_PROVIDER` | Optional | `"OPENAI"` | Model provider selector (`"OPENAI"`, `"ANTHROPIC"`, `"OLLAMA"`). Raises `ValueError` if unrecognized. |
| `DEFAULT_MODEL_NAME` | Optional | `"gpt-4o"` | Target LLM model name passed to `ChatOpenAI` or `ChatAnthropic`. |
| `DEFAULT_MODEL_TEMPERATURE` | Optional | `"0"` | Model sampling temperature (parsed to `int`). |
| `OPENAI_API_KEY` | Required if OPENAI | None | Secret API key for OpenAI LLM requests. |
| `ANTHROPIC_API_KEY` | Required if ANTHROPIC | None | Secret API key for Anthropic LLM requests. |

*Special Note for OLLAMA*: When `DEFAULT_MODEL_PROVIDER="OLLAMA"`, `config.py` sets `openai_api_key="ollama"` and `openai_api_base="http://IPADDRESS:11434/v1"`.

### 2.3 LLM API Client Requirements
- Each agent module (`agent_smith`, `hermes`, `software_engineer`, `tool_maker`, `web_researcher`) calls `config.default_langchain_model.bind_tools(tools)`.
- ReAct execution loop invokes `tooled_up_model.invoke(messages)`, sending HTTP requests to the active provider API endpoint.

### 2.4 Offline Mocking Requirements for E2E Execution
1. **LLM Model Mocking**:
   - Intercept `config.default_langchain_model.bind_tools` or replace `config.default_langchain_model` with a fake/mock runnable that returns synthetic `AIMessage` instances (with pre-configured `tool_calls` or text content).
2. **SQLite Checkpointer Isolation**:
   - `utils.py` creates global `conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)` at module load time.
   - Offline test suites must patch `utils.conn` to use in-memory SQLite (`sqlite3.connect(":memory:")`) or temp files to prevent database file creation/pollution in test working directories.
3. **Interactive Console Input Mocking**:
   - `hermes.py` (`feedback_and_wait_on_human_input`) blocks on `input("> ")`.
   - `sovereign_gate.py` (`console_approval_handler`) blocks on `input(" Approve tool execution? (y/N): ")`.
   - Headless test execution requires mocking `builtins.input` (e.g. `unittest.mock.patch('builtins.input')`).
4. **FileSystem / Dynamic Import Side-Effects**:
   - `agent_smith.py` performs top-level file reads at import time (lines 12-16):
     ```python
     with open(f"agents/{example_agent}.py", 'r') as file: ...
     with open(f"tests/agents/test_{example_agent}.py", 'r') as file: ...
     ```
     This fails if the current working directory is not the project root. offline tests must ensure CWD or file-open mocking.
   - `utils.load_module` registers modules into `sys.modules`. Offline test cleanup must purge dynamic `gensym` modules from `sys.modules`.
5. **External Tool Execution Mocking**:
   - Web search (`duck_duck_go_web_search`) and web fetch (`fetch_web_page_content`) tools make external HTTP requests.
   - Shell execution tools (`run_shell_command`, `run_command`) run arbitrary subprocess commands.

---

## 3. Security Boundary Mechanisms & Protected Path Policies (`sovereign_gate.py`)

### 3.1 Hardcoded Protected Paths
`sovereign_gate.py` defines an explicit `PROTECTED_PATHS` set:
1. `/Users/ricardo/AgentK/agent_kernel.py`
2. `/Users/ricardo/AgentK/agents/sdk_bridge.py`
3. `/Users/ricardo/AgentK/agents/sovereign_gate.py`
4. `/Users/ricardo/AgentK/self_heal.sh`
5. `/Users/ricardo/AgentK/requirements.txt`
6. `/Users/ricardo/AgentK/tools/assign_agent_to_task.py`

*Portability Vulnerability*: These paths are hardcoded to `/Users/ricardo/AgentK/...`. Moving the project directory breaks absolute path matching unless normalized dynamically.

### 3.2 Security Rules & Policy Enforcement Hierarchy
`get_sovereign_policies()` constructs a 6-layer policy pipeline using `google.antigravity.hooks.policy`:

1. **Rule 1 — Direct File Protection (`policy.deny`)**:
   - Target tools: `write_to_file`, `replace_file_content`, `multi_replace_file_content`, `create_file`, `edit_file`, `overwrite_file`, `delete_file`.
   - Condition: `_deny_protected_writes` checks tool arguments (`path`, `TargetFile`, `source`, `dest`, `filename`, `filepath`) and `canonical_path` against `is_protected_path`. Also blocks modifications to `.git`.
2. **Rule 2 — Agent/Tool Meta-Modification Interception (`policy.ask_user`)**:
   - Target tools: Same write tool set.
   - Condition: `_is_agent_or_tool_write` triggers if target path resides inside `agents/` or `tools/`.
   - Handler: `console_approval_handler` asks terminal operator for `y/N` confirmation.
3. **Rule 3 — Dangerous Shell Command Denial (`policy.deny`)**:
   - Target tools: `run_command`, `run_shell_command`.
   - Condition: `_deny_dangerous_commands` inspects `CommandLine` argument string. If command mentions any protected filename or `.git` AND contains any write/delete operator (`>`, `>>`, `rm`, `mv`, `chmod`, `sed`, `tee`), command execution is denied outright.
4. **Rule 4 — General Shell Command Gatekeeping (`policy.ask_user`)**:
   - Target tools: `run_command`, `run_shell_command`.
   - Handler: `console_approval_handler` requires operator approval for all remaining shell execution.
5. **Rule 5 — Subagent Fork Protection (`policy.ask_user`)**:
   - Target tools: `start_subagent`, `invoke_subagent`, `define_subagent`, `browser_subagent`, `assign_agent_to_task`.
   - Handler: `console_approval_handler` requires operator approval to prevent unauthorized subagent recursion/fork-bombs.
6. **Rule 6 — Fallback Rule (`policy.allow("*")`)**:
   - Permits all other read-only and unconstrained operations.

---

## 4. Complete Input Requirements & Parameter Defaults

Below is the exhaustive parameter specification table across all 9 modules:

| Module | Function / Entry Point | Parameter | Parameter Type | Default Value | Required / Optional |
|---|---|---|---|---|---|
| `agent_smith.py` | `agent_smith` | `task` | `str` | None | **Required** |
| `agent_smith.py` | `reasoning` | `state` | `MessagesState` | None | **Required** |
| `agent_smith.py` | `check_for_tool_calls` | `state` | `MessagesState` | None | **Required** |
| `hermes.py` | `hermes` | `uuid` | `str` | None | **Required** |
| `hermes.py` | `feedback_and_wait_on_human_input` | `state` | `MessagesState` | None | **Required** |
| `hermes.py` | `check_for_exit` | `state` | `MessagesState` | None | **Required** |
| `hermes.py` | `reasoning` | `state` | `MessagesState` | None | **Required** |
| `hermes.py` | `check_for_tool_calls` | `state` | `MessagesState` | None | **Required** |
| `software_engineer.py` | `software_engineer` | `task` | `str` | None | **Required** |
| `software_engineer.py` | `reasoning` | `state` | `MessagesState` | None | **Required** |
| `software_engineer.py` | `check_for_tool_calls` | `state` | `MessagesState` | None | **Required** |
| `tool_maker.py` | `tool_maker` | `task` | `str` | None | **Required** |
| `tool_maker.py` | `reasoning` | `state` | `MessagesState` | None | **Required** |
| `tool_maker.py` | `check_for_tool_calls` | `state` | `MessagesState` | None | **Required** |
| `web_researcher.py` | `web_researcher` | `task` | `str` | None | **Required** |
| `web_researcher.py` | `reasoning` | `state` | `MessagesState` | None | **Required** |
| `web_researcher.py` | `check_for_tool_calls` | `state` | `MessagesState` | None | **Required** |
| `sdk_bridge.py` | `dispatch_agent` | `agent_name` | `str` | None | **Required** |
| `sdk_bridge.py` | `dispatch_agent` | `task` | `str` | None | **Required** |
| `sovereign_gate.py` | `is_protected_path` | `path` | `str \| None` | None | **Required** |
| `sovereign_gate.py` | `_is_agent_or_tool_write` | `tc` | `types.ToolCall` | None | **Required** |
| `sovereign_gate.py` | `_deny_protected_writes` | `tc` | `types.ToolCall` | None | **Required** |
| `sovereign_gate.py` | `_deny_dangerous_commands` | `tc` | `types.ToolCall` | None | **Required** |
| `sovereign_gate.py` | `console_approval_handler` | `tc` | `types.ToolCall` | None | **Required** |
| `utils.py` | `all_agents` | `exclude` | `list[str]` | `["hermes"]` | Optional |
| `utils.py` | `gensym` | `length` | `int` | `32` | Optional |
| `utils.py` | `gensym` | `prefix` | `str` | `"gensym_"` | Optional |
| `utils.py` | `load_module` | `source` | `str` | None | **Required** |
| `utils.py` | `load_module` | `module_name` | `str \| None` | `None` | Optional |

---

## 5. Handoff Protocol (5-Component Standard)

### 1. Observation
- Verified code content and structure across all 9 target files: `sovereign_gate.py` (166 lines), `agent_smith.py` (113 lines), `hermes.py` (120 lines), `software_engineer.py` (73 lines), `tool_maker.py` (143 lines), `web_researcher.py` (61 lines), `sdk_bridge.py` (127 lines), `utils.py` (130 lines), `config.py` (23 lines).
- Type hints on `agent_smith`, `software_engineer`, `tool_maker`, `web_researcher` declare `-> str`, but return values from `graph.invoke(...)` are runtime dictionary objects (`dict[str, Any]`).
- `sovereign_gate.py` hardcodes absolute user paths (`/Users/ricardo/AgentK/...`).
- `agent_smith.py` executes top-level file read `open("agents/web_researcher.py")` on module import.

### 2. Logic Chain
1. Entry point functions wrap LangGraph `StateGraph.compile().invoke(...)`.
2. Calling `graph.invoke(...)` returns the complete state dict (`MessagesState`), whereas the return type annotation specifies `str`.
3. `sdk_bridge.py` handles this mismatch in `dispatch_agent` by extracting `result["messages"][-1].content`.
4. Therefore, direct callers expecting a `str` will receive a `dict` unless wrapped by `sdk_bridge` or refactored.
5. In `sovereign_gate.py`, security path checking relies on exact string match with `PROTECTED_PATHS`. Absolute hardcoded paths will fail on any other environment or user directory.

### 3. Caveats
- No code execution or test runs were performed during this analysis in compliance with the read-only mandate.
- Web search tools (`duck_duck_go_web_search`) and shell tools (`run_shell_command`) were evaluated via source code inspection only.

### 4. Conclusion
The core agent architecture is modular and cleanly structured around LangGraph and Antigravity SDK. However, end-to-end execution and test isolation require resolving:
1. Return type hint disparities (`dict` vs `str`) across agent functions.
2. Path portability in `sovereign_gate.py` and `agent_smith.py` (replacing hardcoded paths with project root relative resolution).
3. Offline test mocks for LLM calls (`ChatOpenAI`), SQLite checkpointer, console `input()`, and filesystem reads.

### 5. Verification Method
To independently verify this analysis:
1. Execute `python3 -c "import agents.software_engineer as se; print(type(se.software_engineer('test')))"` with mocked LLM to confirm `dict` return type vs `str` annotation.
2. Inspect `sovereign_gate.py` lines 14-21 to verify `PROTECTED_PATHS` absolute path strings.
3. Inspect `agent_smith.py` lines 12-16 to verify top-level file reads.
