# CLI Startup Performance Board

**Repository:** ricardotgomes11/AgentK  
**Branch audited:** 2-forensic-root-recovery  
**Audited head:** dfd9f39c30cf99d6e2fe6a573f7b18dcbd922204  
**Scope:** Read-only static audit of module imports, configuration loading, and discovery.  
**Reported symptom:** CLI startup is approximately four seconds.  
**Measurement status:** The four-second total was supplied as the symptom; no phase timings or local runtime profile were available during this audit. Findings below are code-path evidence, not measured attribution.

## Workstream 1 — Module imports

**Finding**
- `agentk` invokes `docker compose run --rm agentk`; the container entrypoint starts `python agent_kernel.py`.
- `agent_kernel.py` eagerly imports `asyncio`, the Google Antigravity `Agent` / config types / interactive loop, then `agents/sdk_bridge.py`.
- `sdk_bridge.py` imports `utils`. At module import, `utils.py` imports the LangGraph SQLite checkpointer, opens `checkpoints.sqlite`, and executes SQLite PRAGMAs.
- Agent discovery dynamically imports agent modules; several construct LangGraph workflows and tool nodes at module scope.

**Impact assessment:** High-likelihood Python-side startup cost. Eager graph construction and checkpointer initialization are on the startup path before the interactive loop.

**Read-only evidence:** `agentk`, `Dockerfile`, `agent_kernel.py`, `agents/sdk_bridge.py`, `utils.py`, and agent module import headers.

## Workstream 2 — Configuration loading

**Finding**
- `agent_kernel.py` calls `load_dotenv()` before SDK bootstrap.
- `config.py` imports both `ChatOpenAI` and `ChatAnthropic` unconditionally, even though only one provider branch is selected.
- Importing `config.py` constructs the selected provider client at module scope. The default provider is OPENAI and the default model is `gpt-4o`.
- The bridge's agent inventory imports multiple agents that themselves import `config`; Python's module cache should prevent repeated execution of the same `config.py` module in the normal process, but the first import still pays the provider import/client construction cost.
- The current bootstrap does not directly import the legacy Hermes module; configuration is pulled in indirectly while enumerating agent modules.

**Impact assessment:** Medium-to-high candidate. The unconditional second provider import is avoidable; client construction is also unnecessarily coupled to importing an agent module.

**Read-only evidence:** `config.py`, `agent_kernel.py`, `agents/agent_smith.py`, `agents/software_engineer.py`, `agents/tool_maker.py`, and `agents/web_researcher.py`.

## Workstream 3 — Plugin / agent discovery

**Finding**
- No separate plugin-discovery framework or plugin registry was found in the audited branch.
- `get_tool_inventory()` calls `utils.list_tools()`, which only scans the `tools/` directory and sorts names. It does not import each tool, so this portion is likely low cost.
- `get_agent_inventory()` calls `utils.all_agents(exclude=["hermes"])`. That function scans `agents/`, dynamically imports every discovered Python file, reads its docstring, and unloads it.
- The scan includes `agents/sdk_bridge.py` as if it were an agent. It is not an agent entry and is imported only to fail the subsequent attribute lookup.
- The other discovered modules include agent implementations that import LangChain/LangGraph, tools, configuration, and compile graphs at module scope.

**Impact assessment:** Highest-confidence avoidable discovery cost. Discovery imports executable agent implementations merely to display names/descriptions; the bridge file is also a false-positive candidate.

**Read-only evidence:** `agents/sdk_bridge.py`, `utils.py`, `agents/agent_smith.py`, `agents/software_engineer.py`, `agents/sovereign_gate.py`, `agents/tool_maker.py`, `agents/web_researcher.py`, and `tools/list_available_agents.py`.

## Ranked fixes

1. **Make agent discovery metadata-only.** Read agent names/descriptions from lightweight metadata (or a small manifest) rather than importing every agent module. Explicitly exclude `sdk_bridge.py` and other infrastructure modules from the agent inventory. Defer loading an agent until it is selected. This removes repeated module execution and graph construction from the startup path.
2. **Defer checkpointer initialization.** Move SQLite connection creation, WAL setup, and checkpointer construction out of `utils.py` module scope. Initialize persistence when a conversation/session actually starts.
3. **Make provider configuration lazy and provider-specific.** Import only the selected LangChain provider and instantiate its client on first use, not while building the startup inventory. Preserve existing environment-variable defaults and provider behavior.
4. **Measure Docker/Compose separately from Python startup.** The launcher creates a fresh one-off container with `docker compose run --rm` on every invocation. Record compose/container creation time separately from Python process/import time before changing the lifecycle. If the measured Docker portion dominates, evaluate a warm service plus `docker compose exec`; do not assume this is the cause without timings.
5. **Keep tool discovery as filename-only enumeration.** It is already substantially lighter than agent discovery; avoid changing it unless profiling shows it matters.

## Verification plan

- Capture repeated cold and warm timings for: shell-to-container start, Python process start, Antigravity imports, bridge import, checkpointer initialization, agent inventory, policy construction, and interactive-loop readiness.
- Use Python import-time tracing for the interpreter phase and explicit monotonic timestamps around the named bootstrap stages.
- Compare the baseline against one change at a time. Require identical agent/tool inventories and successful interactive startup.
- Do not treat the four-second end-to-end number as evidence for any one cause until the phase timings are collected.

## Execution state

- Source files were inspected only; no source code, runtime configuration, dependencies, or tests were changed.
- No independent worker processes were available in this execution surface. The three requested scopes were inspected as separate read-only workstreams and consolidated here.
- No CLI benchmark or test suite was run.