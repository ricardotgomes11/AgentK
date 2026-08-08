# Project Analysis & Requirement Synthesis — AgentK

## Executive Summary
This analysis examines the AgentK codebase located at `/Users/ricardo/AgentK/` and its specification status in `/Users/ricardo/AgentK/agents/.agents/ORIGINAL_REQUEST.md`.

- **Original Request File Status**: `/Users/ricardo/AgentK/agents/.agents/ORIGINAL_REQUEST.md` is currently an unpopulated draft template containing `[TBD]` placeholders for project goals, requirements, and acceptance criteria.
- **Codebase Reality**: The existing implementation in `/Users/ricardo/AgentK/` defines a functional autoagentic AGI system ("AgentK"). It uses a small core kernel of agents (Hermes, Agent Smith, Tool Maker, Software Engineer, Web Researcher), connected to the Google Antigravity SDK via `sdk_bridge.py`, guarded by a security policy gate (`sovereign_gate.py`), and backed by SQLite state checkpointers (`utils.py`).

---

## 1. Evidence Chain & Codebase Findings

### Observation 1.1: Draft Specification in `ORIGINAL_REQUEST.md`
- **File Location**: `/Users/ricardo/AgentK/agents/.agents/ORIGINAL_REQUEST.md` (Lines 1-27)
- **Verbatim Snippet**:
  ```markdown
  # Teamwork Project Prompt — Draft
  > Status: Step 1 — Eliciting project idea
  > Goal: Craft prompt → get user approval → delegate to teamwork_preview
  [Project description — 1-2 sentences]
  Working directory: [TBD]
  ## Requirements
  ### R1. [TBD]
  ### R2. [TBD]
  ## Acceptance Criteria
  ### [TBD]
  - [ ] [TBD]
  ```
- **Finding**: The top-level `ORIGINAL_REQUEST.md` file is a draft template. The concrete project structure and functional goals are embedded directly in the codebase files and docstrings under `/Users/ricardo/AgentK/agents/` and the root directory.

### Observation 1.2: Architecture & Core Components of AgentK
- **File Locations**:
  - `/Users/ricardo/AgentK/agents/agent_smith.py`
  - `/Users/ricardo/AgentK/agents/hermes.py`
  - `/Users/ricardo/AgentK/agents/sdk_bridge.py`
  - `/Users/ricardo/AgentK/agents/software_engineer.py`
  - `/Users/ricardo/AgentK/agents/sovereign_gate.py`
  - `/Users/ricardo/AgentK/agents/tool_maker.py`
  - `/Users/ricardo/AgentK/agents/web_researcher.py`
  - `/Users/ricardo/AgentK/agent_kernel.py`
  - `/Users/ricardo/AgentK/utils.py`
  - `/Users/ricardo/AgentK/config.py`

- **Key System Architecture Elements**:
  1. **Google Antigravity SDK Outer Bootloader**:
     - `agent_kernel.py` serves as the SDK entry point. It sets up crash resilience (`SIGPIPE` handling, safe stream flushing on exit), loads environment variables via `dotenv`, and instantiates `google.antigravity.Agent` using `LocalAgentConfig`.
  2. **Control Plane Security Gate (`sovereign_gate.py`)**:
     - Defines `PROTECTED_PATHS` including `/Users/ricardo/AgentK/agent_kernel.py`, `sdk_bridge.py`, `sovereign_gate.py`, `self_heal.sh`, `requirements.txt`, `assign_agent_to_task.py`, and `.git`.
     - Implements policy rules (`get_sovereign_policies`):
       - Explicitly denies file writes/deletions targeting protected paths (`_deny_protected_writes`).
       - Denies dangerous shell commands modifying core scripts (`_deny_dangerous_commands`).
       - Requires console approval (`ask_user` with `console_approval_handler`) for agent/tool creations, shell commands, and subagent invocations.
  3. **SDK Bridge Layer (`sdk_bridge.py`)**:
     - Bridges the `google-antigravity` SDK with existing LangGraph agents without modifying agent source code.
     - Provides `get_agent_inventory()`, `get_tool_inventory()`, `get_system_prompt()`, and `dispatch_agent(agent_name, task)`.
  4. **Kernel Agents Core**:
     - **Hermes** (`hermes.py`): ReAct orchestrator graph managing goal understanding, plan generation, agent task assignment (`assign_agent_to_task`), and interactive user feedback loop (`feedback_and_wait_on_human_input`). Uses `SqliteSaver` checkpointer (`checkpoints.sqlite`).
     - **AgentSmith** (`agent_smith.py`): ReAct agent architect that designs and writes new LangGraph agents in `agents/` and smoke tests in `tests/agents/`.
     - **ToolMaker** (`tool_maker.py`): ReAct tool developer creating `@tool`-decorated functions in `tools/` and unit tests in `tests/tools/`. Handles package installs (`requirements.txt`, `apt-packages-list.txt`).
     - **SoftwareEngineer** (`software_engineer.py`): ReAct code manager equipped with file operations (`write_to_file`, `overwrite_file`, `delete_file`, `read_file`), shell execution (`run_shell_command`), and task delegation tools.
     - **WebResearcher** (`web_researcher.py`): Knowledge gatherer using `duck_duck_go_web_search` and `fetch_web_page_content`.
  5. **Dynamic Reflection & Utilities (`utils.py`)**:
     - Performs dynamic module loading (`load_module`, `gensym`), agent/tool listing (`list_agents`, `list_tools`, `all_agents`, `all_tool_functions`), and broken code detection (`list_broken_tools`, `list_broken_agents`).

---

## 2. Synthesis of Requirements & Features

Based on codebase evidence, the core requirements for AgentK are:

1. **System Integrity & Control Plane Protection (R1)**:
   - Must prevent autonomous agents from tampering with critical system files (`agent_kernel.py`, `sovereign_gate.py`, `sdk_bridge.py`, `.git`).
   - Must intercept high-impact actions (file writes to `agents/` or `tools/`, shell commands, subagent creation) and request creator authorization.

2. **Self-Evolution & Dynamic Extensibility (R2)**:
   - Must support dynamic agent creation by Agent Smith with required smoke tests.
   - Must support dynamic tool creation by Tool Maker with unit tests passing via `unittest`.
   - Must dynamically reflect newly created tools and agents into `utils.py` and the SDK bridge without restarting the system.

3. **Orchestration & State Persistence (R3)**:
   - Hermes must orchestrate sequential task execution, delegating tasks to sub-agents.
   - Conversation state and execution checkpoints must be persisted via SQLite checkpointer (`checkpoints.sqlite`).

4. **Resilience & Testing Quality Assurance (R4)**:
   - System must gracefully handle stream errors (`SIGPIPE`) and process crashes.
   - All tools and agents must have co-located unit/smoke tests with automated breakage detection (`list_broken_tools`, `list_broken_agents`).

---

## 3. Proposed Milestone Decomposition

### Milestone 1: Control Plane Security & Gate Validation
- **Objective**: Verify and harden Sovereign Gate security policies to prevent rogue self-evolution and protect kernel integrity.
- **Key Features**:
  - Path protection for `PROTECTED_PATHS` across all file manipulation tools.
  - Interactive approval handler integration (`console_approval_handler`) for high-impact actions.
  - Shell command static analysis blocking unauthorized script overwrites.
- **Acceptance Criteria**:
  - Attempts to edit/delete `agent_kernel.py`, `sovereign_gate.py`, or `.git` return access denied.
  - Creating a file under `agents/` or `tools/` triggers user approval prompt.
  - `agent_kernel.py` boots cleanly with policies active.

### Milestone 2: Agent & Tool Self-Evolution Pipeline
- **Objective**: Ensure end-to-end reliability of Agent Smith and Tool Maker dynamic code generation.
- **Key Features**:
  - Tool creation workflow: `@tool` function written to `tools/<tool_name>.py`, unit test written to `tests/tools/test_<tool_name>.py`, `unittest` verification.
  - Agent creation workflow: LangGraph ReAct workflow written to `agents/<agent_name>.py`, smoke test written to `tests/agents/test_<agent_name>.py`.
  - Dynamic dependency management via `requirements.txt` and `apt-packages-list.txt`.
- **Acceptance Criteria**:
  - Tool Maker successfully writes and passes tests for new custom tools.
  - Agent Smith writes and verifies new agents without missing tool imports or broken graph edges.
  - `utils.list_tools()` and `utils.list_agents()` immediately reflect newly added files.

### Milestone 3: Hermes Multi-Agent Orchestration & Bridge Integration
- **Objective**: Validate end-to-end task planning, agent delegation, and SDK bridge interaction.
- **Key Features**:
  - Hermes goal understanding and plan formulation.
  - Task dispatching via `assign_agent_to_task` and `sdk_bridge.dispatch_agent`.
  - Conversation state tracking in SQLite (`checkpoints.sqlite`).
- **Acceptance Criteria**:
  - Multi-step requests are broken into discrete subtasks and assigned to appropriate agents.
  - State is saved and resumed across turns without losing history.
  - `sdk_bridge.get_system_prompt()` accurately combines kernel agent docstrings and tool inventory.

### Milestone 4: Test Hardening, Diagnostics & Self-Healing
- **Objective**: Build a complete test suite for kernel components and implement automated health monitoring.
- **Key Features**:
  - Complete test coverage for `hermes.py`, `agent_smith.py`, `tool_maker.py`, `sovereign_gate.py`, `sdk_bridge.py`.
  - Failure reporting via `list_broken_tools()` and `list_broken_agents()`.
  - Automated recovery via `self_heal.sh`.
- **Acceptance Criteria**:
  - All test files under `tests/` execute cleanly with zero errors.
  - Intentionally introducing syntax/import errors into a test tool is caught by `list_broken_tools()`.
  - `self_heal.sh` restores git repository state if critical files are corrupted.
