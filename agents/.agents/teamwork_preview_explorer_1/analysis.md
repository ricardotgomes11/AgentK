# Comprehensive Technical Analysis: AgentK Python Agent Modules

## Executive Summary

This report presents a complete code inspection and architectural analysis of the seven Python modules located in `/Users/ricardo/AgentK/agents/`:
1. `agent_smith.py` — Agent Architect & Bootstrapper
2. `hermes.py` — High-Level User Orchestration Agent
3. `sdk_bridge.py` — Google Antigravity SDK Integration Layer
4. `software_engineer.py` — Codebase & Workspace Operations Agent
5. `sovereign_gate.py` — Policy Enforcement & Control-Plane Security Gate
6. `tool_maker.py` — LangChain Tool Creator & Dependency Manager
7. `web_researcher.py` — Online Information Gathering Agent

All seven modules form the core agentic runtime of **AgentK**, a self-evolving multi-agent system built on top of `LangGraph`, `LangChain`, and `google-antigravity`.

---

## 1. System Architecture & Module Interconnections

### Data & Control Flow Matrix

```
                      +-------------------+
                      |   Human / User    |
                      +---------+---------+
                                |
               +----------------+----------------+
               |                                 |
               v                                 v
      +-----------------+              +-------------------+
      |   hermes.py     |              |   sdk_bridge.py   |
      | (Interactive    |              | (SDK Entry Point &|
      |  Orchestrator)  |              | Dynamic Dispatch) |
      +--------+--------+              +---------+---------+
               |                                 |
               +----------------+----------------+
                                |
                                v
           +-------------------------------------------+
           |           Specialized Sub-Agents           |
           |  (Dispatched via assign_agent_to_task)    |
           +-------+--------------------+--------------+
                   |                    |
       +-----------+--+          +------+-----------+          +-------------------+
       | agent_smith  |          |  tool_maker      |          | software_engineer |
       | (Creates     |          | (Creates tools   |          | & web_researcher  |
       |  agents)     |          |  & dependencies) |          | (Domain execution)|
       +-------+------+          +------+-----------+          +-------------------+
               |                        |
               +-----------+------------+
                           |
                           v
           +-------------------------------------------+
           |            sovereign_gate.py              |
           | (Policy hook interceptor: denies/approves |
           |  file modifications & shell commands)     |
           +-------------------------------------------+
```

### Module Interaction Mechanics

1. **User Interaction Entry Points**:
   - **`hermes.py`**: Command-line interactive ReAct orchestrator. Evaluates user goals, builds sequential plans, delegates subtasks using `assign_agent_to_task`, and persists state in SQLite (`checkpoints.sqlite`).
   - **`sdk_bridge.py`**: Programmatic bridge for external invocation via Google Antigravity SDK. Exposes system prompts, agent inventories (`utils.all_agents`), and dynamic dispatch (`dispatch_agent`).

2. **Self-Evolution Loop**:
   - **`agent_smith.py`**: Designs and writes new LangGraph agents (`agents/<name>.py`) and test suites (`tests/agents/test_<name>.py`). Invokes `tool_maker` when required capabilities do not exist.
   - **`tool_maker.py`**: Writes single `@tool`-decorated functions into `tools/<name>.py` and corresponding `unittest` test suites in `tests/tools/test_<name>.py`. Updates `requirements.txt` / `apt-packages-list.txt` as needed.

3. **Domain Execution Agents**:
   - **`software_engineer.py`**: Handles code modification, file inspection/deletion, shell commands, and agent assignment.
   - **`web_researcher.py`**: Queries search engines (`duck_duck_go_web_search`) and scrapes web content (`fetch_web_page_content`).

4. **Governance & Control Plane Protection**:
   - **`sovereign_gate.py`**: Registers security policies using `google.antigravity.hooks.policy`. Denies direct modifications to critical system paths (including `agent_kernel.py`, `sdk_bridge.py`, `sovereign_gate.py`, `.git`) and prompts for interactive user approval on sensitive file/shell operations.

---

## 2. Detailed Module Inspection

### 2.1 `agent_smith.py`

- **Purpose**: ReAct agent that engineers new ReAct agents using LangGraph.
- **Imports**:
  - `typing.Literal`
  - `langchain_core.messages.HumanMessage`, `SystemMessage`
  - `langgraph.graph.END`, `StateGraph`, `MessagesState`
  - `langgraph.prebuilt.ToolNode`
  - `config`
  - `utils`
- **Class Definitions**: None (functional LangGraph pipeline).
- **Functions & Signatures**:
  - `reasoning(state: MessagesState) -> dict`: Evaluates message history using LLM model bound with all tool functions from `utils.all_tool_functions()`.
  - `check_for_tool_calls(state: MessagesState) -> Literal["tools", END]`: Routes execution to `tools` node if LLM generated tool calls, otherwise terminates (`END`).
  - `agent_smith(task: str) -> dict` (annotated as returning `str`, actually returns LangGraph state dict): Primary entry point function.
- **Data Flow**:
  - `SystemMessage(system_prompt)` + `HumanMessage(task)` -> `reasoning` node -> `check_for_tool_calls` -> (`ToolNode(tools)` -> `reasoning`) OR `END`.
- **Implementation Status & Vulnerabilities**:
  - **Implemented**: Full ReAct graph compile, prompt template injection with exemplar code (`agents/web_researcher.py` & `tests/agents/test_web_researcher.py`).
  - **Flaws/Issues**:
    - **Top-Level File Input Dependency** (Lines 12–16): Opens `agents/web_researcher.py` and `tests/agents/test_web_researcher.py` at module import time using relative file paths. If the module is imported when CWD is not the project root, it raises `FileNotFoundError`.
    - **Return Type Annotation Mismatch** (Line 109): Signature indicates `-> str`, but `graph.invoke` returns `dict[str, Any]` containing `messages`.
    - **Global Tool Binding**: Binds *all* tools in `tools/` directory, exposing potentially unrelated tools to the agent maker.

---

### 2.2 `hermes.py`

- **Purpose**: Top-level orchestrator agent managing multi-agent goals and user dialog.
- **Imports**:
  - `typing.Literal`
  - `langchain_core.messages.HumanMessage`, `SystemMessage`
  - `langgraph.graph.StateGraph`, `MessagesState`, `END`
  - `langgraph.prebuilt.ToolNode`
  - `utils`, `config`
  - `tools.list_available_agents.list_available_agents`
  - `tools.assign_agent_to_task.assign_agent_to_task`
- **Class Definitions**: None.
- **Functions & Signatures**:
  - `feedback_and_wait_on_human_input(state: MessagesState) -> dict`: Prompts user via standard input (`input("> ")`) and appends `HumanMessage`.
  - `check_for_exit(state: MessagesState) -> Literal["reasoning", END]`: Checks if user input equals `"exit"`.
  - `reasoning(state: MessagesState) -> dict`: Generates agent response using LLM bound with `list_available_agents` and `assign_agent_to_task`.
  - `check_for_tool_calls(state: MessagesState) -> Literal["tools", "feedback_and_wait_on_human_input"]`: Tool call router.
  - `hermes(uuid: str) -> dict`: Main session runner, compiles graph with SQLite checkpointer (`utils.checkpointer`) and executes given session `uuid`.
- **Data Flow**:
  - Starts at `feedback_and_wait_on_human_input` -> `check_for_exit` -> `reasoning` -> `check_for_tool_calls` -> `tools` -> `reasoning` -> `feedback_and_wait_on_human_input`.
- **Implementation Status & Vulnerabilities**:
  - **Implemented**: Stateful conversation persistence via `SqliteSaver`, user feedback loop, tool assignment.
  - **Flaws/Issues**:
    - **Static Prompt Evaluation** (Line 43): Calls `list_available_agents.invoke({})` during top-level system prompt initialization at module load. Dynamic agents created during session runtime will not be reflected in system prompt without reloading.
    - **Blocking Standard Input**: Relies on synchronous CLI `input("> ")` which blocks thread execution and prevents non-interactive programmatic use.

---

### 2.3 `sdk_bridge.py`

- **Purpose**: Interoperability bridge connecting AgentK to Google Antigravity SDK interfaces.
- **Imports**:
  - `os`, `sys`, `sqlite3`, `traceback`
  - Dynamic path insertion of `AGENTK_ROOT` and root project directory into `sys.path`.
  - Conditional import of `utils` with error capture (`_UTILS_AVAILABLE`).
- **Class Definitions**: None.
- **Functions & Signatures**:
  - `get_agent_inventory() -> str`: Formats non-Hermes agents and docstrings.
  - `get_tool_inventory() -> str`: Formats sorted list of available tools.
  - `get_system_prompt() -> str`: Composes unified system prompt merging kernel identity and live tool/agent snapshots.
  - `dispatch_agent(agent_name: str, task: str) -> str`: Loads `agents/{agent_name}.py` dynamically via `utils.load_module`, executes agent function, extracts final response string (`result["messages"][-1].content`), and cleans up `sys.modules`.
- **Data Flow**:
  - `dispatch_agent` -> `utils.load_module` -> `agent_function(task=task)` -> extracts `response` -> returns string output or formatted stack trace on error.
- **Implementation Status & Vulnerabilities**:
  - **Implemented**: Robust error handling, path resolution, dynamic module execution, inventory reflection.
  - **Flaws/Issues**:
    - **Assumed Function Interface**: Assumes all agents take keyword argument `task: str` and return a dict with a `"messages"` list key. `hermes(uuid: str)` breaks this interface contract.

---

### 2.4 `software_engineer.py`

- **Purpose**: General-purpose coding agent capable of file CRUD operations, shell execution, and subtask delegation.
- **Imports**:
  - `typing.Literal`
  - `langchain_core.messages.HumanMessage`, `SystemMessage`
  - `langgraph.graph.END`, `StateGraph`, `MessagesState`
  - `langgraph.prebuilt.ToolNode`
  - `config`
  - Tools: `write_to_file`, `overwrite_file`, `delete_file`, `read_file`, `run_shell_command`, `assign_agent_to_task`, `list_available_agents`.
- **Class Definitions**: None.
- **Functions & Signatures**:
  - `reasoning(state: MessagesState) -> dict`: LLM reasoning node.
  - `check_for_tool_calls(state: MessagesState) -> Literal["tools", END]`: Tool call router.
  - `software_engineer(task: str) -> dict`: Invokes graph with human task.
- **Implementation Status & Vulnerabilities**:
  - **Implemented**: Clean 7-tool suite integration, concise system prompt.
  - **Flaws/Issues**:
    - Return type annotation indicates `-> str` but returns state dict `{"messages": [...]}`.

---

### 2.5 `sovereign_gate.py`

- **Purpose**: Security policies and interactive approval gates protecting core system integrity from rogue agent self-evolution or command execution.
- **Imports**:
  - `os`
  - `google.antigravity.hooks.policy`
  - `google.antigravity.types`
- **Class Definitions**: None.
- **Functions & Signatures**:
  - `is_protected_path(path: str | None) -> bool`: Checks if absolute path matches `PROTECTED_PATHS` or `.git` directory.
  - `_is_agent_or_tool_write(tc: types.ToolCall) -> bool`: Detects tool calls attempting file edits inside `agents/` or `tools/`.
  - `_deny_protected_writes(tc: types.ToolCall) -> bool`: Checks if tool call parameters target protected paths.
  - `_deny_dangerous_commands(tc: types.ToolCall) -> bool`: Inspects command line string for write/delete operators (`>`, `rm`, `mv`, `chmod`, `sed`, `tee`) targeting protected filenames.
  - `console_approval_handler(tc: types.ToolCall) -> bool`: Prompts operator on terminal for confirmation (`y/N`).
  - `get_sovereign_policies() -> list[policy.Policy]`: Compiles 6 policy tiers (deny protected writes, approve agent/tool creation, deny shell writes to protected files, approve shell execution, approve subagents, fallback allow).
- **Implementation Status & Vulnerabilities**:
  - **Implemented**: Comprehensive policy definitions using `google.antigravity` policy framework.
  - **Flaws/Issues**:
    - **Hardcoded Path Strings**: `PROTECTED_PATHS` set contains hardcoded user-specific path `/Users/ricardo/AgentK/...`. Portability across different deployment environments requires relative resolution or environment variables.
    - **Heuristic Command Inspection**: `_deny_dangerous_commands` uses simple string inclusion (`if kw in cmd`), which can trigger false positives (e.g. `cat agent_kernel.py`) or be bypassed by shell alias tricks, subshells, or python script invocations.

---

### 2.6 `tool_maker.py`

- **Purpose**: Specialized agent for writing LangChain tool functions (`@tool`) and unit tests.
- **Imports**:
  - `typing.Literal`
  - `langchain_core.messages.HumanMessage`, `SystemMessage`
  - `langgraph.graph.END`, `StateGraph`, `MessagesState`
  - `langgraph.prebuilt.ToolNode`
  - `utils`, `config`
- **Class Definitions**: None.
- **Functions & Signatures**:
  - `reasoning(state: MessagesState) -> dict`: LLM node bound with all tools from `utils.all_tool_functions()`.
  - `check_for_tool_calls(state: MessagesState) -> Literal["tools", END]`: Tool router.
  - `tool_maker(task: str) -> dict`: Main entry point function.
- **Implementation Status & Vulnerabilities**:
  - **Implemented**: Full ReAct graph, detailed prompt instructions with tool and unittest code examples.
  - **Flaws/Issues**:
    - **OS Context Mismatch**: System prompt states `"You are running on Debian 11"`, whereas host workspace is macOS (Darwin x86_64/arm64). Package installation instructions (`apt-get`) will fail on non-Linux hosts without Docker containment.
    - **Prompt Spelling Typo**: Line 37 contains `"succintly"`.
    - Return type mismatch (`-> str` vs dict).

---

### 2.7 `web_researcher.py`

- **Purpose**: Research agent dedicated to web queries and document scraping.
- **Imports**:
  - `typing.Literal`
  - `langchain_core.messages.HumanMessage`, `SystemMessage`
  - `langgraph.graph.END`, `StateGraph`, `MessagesState`
  - `langgraph.prebuilt.ToolNode`
  - `config`
  - Tools: `tools.duck_duck_go_web_search.duck_duck_go_web_search`, `tools.fetch_web_page_content.fetch_web_page_content`.
- **Class Definitions**: None.
- **Functions & Signatures**:
  - `reasoning(state: MessagesState) -> dict`: LLM reasoning node.
  - `check_for_tool_calls(state: MessagesState) -> Literal["tools", END]`: Tool router.
  - `web_researcher(task: str) -> dict`: Main entry point function.
- **Implementation Status & Vulnerabilities**:
  - **Implemented**: Focused 2-tool setup (`duck_duck_go_web_search`, `fetch_web_page_content`).
  - **Flaws/Issues**:
    - **Prompt Markdown Formatting Error** (Line 12): Unclosed triple backticks (```` ``` ````) in `system_prompt`.
    - Return type mismatch (`-> str` vs dict).

---

## 3. Comparative Analysis & Summary Matrix

| Module | Purpose | Graph Nodes | Key Tools | Return Type | Identified Issues / Deficiencies |
|---|---|---|---|---|---|
| `agent_smith.py` | Agent architect | `reasoning`, `tools` | All (`utils.all_tool_functions`) | `dict` (annotated `str`) | Hardcoded relative paths at module load; return type mismatch |
| `hermes.py` | CLI Orchestrator | `feedback_and_wait_on_human_input`, `reasoning`, `tools` | `list_available_agents`, `assign_agent_to_task` | `dict` (unannotated) | Static prompt evaluation at import; CLI blocking `input()` |
| `sdk_bridge.py` | SDK Integration | N/A (Bridge) | N/A | `str` | Assumes `task` kwarg across all agents; fails for `hermes(uuid)` |
| `software_engineer.py` | Workspace & Code ops | `reasoning`, `tools` | 7 explicit file & shell tools | `dict` (annotated `str`) | Return type annotation mismatch |
| `sovereign_gate.py` | Policy Governance | N/A (Policy definitions) | N/A | `list[Policy]` | Hardcoded user paths (`/Users/ricardo/...`); simple heuristic command checks |
| `tool_maker.py` | Tool developer | `reasoning`, `tools` | All (`utils.all_tool_functions`) | `dict` (annotated `str`) | Hardcoded OS prompt ("Debian 11"); return type mismatch |
| `web_researcher.py` | Web research | `reasoning`, `tools` | DDG Search, Web Fetch | `dict` (annotated `str`) | Unclosed markdown backticks in prompt; return type mismatch |

---

## 4. Dependencies & Framework Requirements

1. **Core Frameworks**:
   - `langgraph` (v0.2.0): State graph compilation, nodes, prebuilt `ToolNode`.
   - `langchain-core` / `langchain-community` (v0.2.11): `SystemMessage`, `HumanMessage`, `@tool` decorators.
   - `langgraph-checkpoint-sqlite`: Checkpoint saver (`SqliteSaver`) used by `hermes.py`.
   - `google-antigravity`: Policy engine (`policy.deny`, `policy.ask_user`, `policy.allow`) used by `sovereign_gate.py`.

2. **Internal Dependencies**:
   - `config.py`: Exports `default_langchain_model`.
   - `utils.py`: Provides `all_tool_functions()`, `all_agents()`, `list_agents()`, `list_tools()`, `load_module()`, `checkpointer`.
   - `tools/`: Atomic tool definitions imported directly or loaded dynamically.
