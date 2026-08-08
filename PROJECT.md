# PROJECT: AgentK — Self-Evolving AGI System Kernel

## Architecture Overview
AgentK is a self-evolving multi-agent system operating on LangGraph and Google Antigravity SDK.
It consists of 5 core specialized agents (Hermes, AgentSmith, ToolMaker, SoftwareEngineer, WebResearcher), an SDK Bridge (`sdk_bridge.py`), a Control Plane Security Policy Engine (`sovereign_gate.py`), dynamic module loading utilities (`utils.py`), and custom tools (`tools/`).

### Core Component Architecture
- **Control Plane (`sovereign_gate.py`)**: Protects core kernel files (`agent_kernel.py`, `sdk_bridge.py`, `sovereign_gate.py`, etc.) and filters destructive shell execution commands.
- **Meta-Agents (`agent_smith.py`, `tool_maker.py`)**: Synthesize new ReAct agents and custom tool functions along with unit tests.
- **Orchestration & Task Agents (`hermes.py`, `software_engineer.py`, `web_researcher.py`)**: Central goal planning, code editing, and web search execution.
- **SDK Bridge (`sdk_bridge.py`)**: Dispatches Antigravity SDK requests to LangGraph agent graphs.

---

## Code Layout
- `agents/`: Core agent graph definitions (`agent_smith.py`, `hermes.py`, `sdk_bridge.py`, `software_engineer.py`, `sovereign_gate.py`, `tool_maker.py`, `web_researcher.py`).
- `tools/`: Dynamic tool functions (`assign_agent_to_task.py`, `delete_file.py`, `read_file.py`, `write_to_file.py`, etc.).
- `tests/`: Unit and integration test suites (`tests/agents/`, `tests/tools/`).
- `utils.py`: Dynamic module loader, tool/agent listing, SQLite checkpointer wrapper.
- `config.py`: Model provider configuration.

---

## Milestones Roadmap

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Control Plane & Path Portability | Refactor `sovereign_gate.py` & `agent_smith.py` for dynamic root resolution; fix `tool_maker` OS prompt; write `test_sovereign_gate.py` & `test_agent_smith.py`. | None | DONE |
| 2 | M2: Agent Interfaces & Quality Fixes | Correct return type annotations (`dict` vs `str`) across agent entry points; fix prompt formatting in `web_researcher` & `tool_maker`; write unit test suites for `software_engineer`, `tool_maker`, `web_researcher`. | M1 | DONE |
| 3 | M3: SDK Bridge & Hermes Orchestration | Refactor `sdk_bridge.py` and `hermes.py` for signature compatibility, non-blocking feedback, and SQLite isolation; write `test_sdk_bridge.py` & `test_hermes.py`. | M2 | DONE |
| 4 | M4: E2E Test Suite & Adversarial Hardening | Pass 100% of E2E Tiers 1-4 test suite; perform Tier 5 white-box adversarial coverage hardening; pass Forensic Integrity Audit. | M3 | DONE |

---

## Interface Contracts

### 1. Sovereign Gate (`sovereign_gate.py`)
- `PROTECTED_PATHS`: Resolved dynamically relative to project root (`Path(__file__).resolve().parents[1]`).
- `get_sovereign_policies() -> list[policy.Policy]`: Returns Antigravity policy objects guarding file writes, deletes, and shell executions.

### 2. Agent Graph Entry Points (`agent_smith`, `software_engineer`, `tool_maker`, `web_researcher`)
- Signature: `def <agent_name>(task: str) -> dict[str, Any]` (or `str` extracted message content where applicable for SDK callers).
- Returns: LangGraph compiled state dictionary containing `"messages"`.

### 3. SDK Bridge (`sdk_bridge.py`)
- Signature: `def run_agent_via_sdk(agent_name: str, task: str, **kwargs) -> str`
- Behavior: Dynamically imports `agents.<agent_name>`, invokes `agent_function(task=task, **kwargs)`, extracts and returns final text response.

---

## Verification & Acceptance Criteria
1. All Python agent modules compile and run cleanly without CWD path sensitivity or hardcoded local path assumptions.
2. Unit test coverage exists for all 7 agent modules under `tests/agents/`, exceeding simple `callable()` assertions.
3. E2E test suite (Tiers 1-4) passes with 100% success rate.
4. Tier 5 Adversarial Coverage Hardening confirms zero untested edge-case paths.
5. Forensic Auditor confirms clean integrity verdict (no hardcoded test outputs or dummy facades).
