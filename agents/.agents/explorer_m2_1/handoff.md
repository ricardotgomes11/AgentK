# Handoff Report: Milestone 2 - Explorer 1 (Agent Interfaces & Return Type Annotations)

## 1. Observation

A detailed static code investigation was performed on all 4 target agent entry point modules in `/Users/ricardo/AgentK/agents/`:
- `agent_smith.py`
- `software_engineer.py`
- `tool_maker.py`
- `web_researcher.py`

Additionally, calling conventions were audited in consumer modules `tools/assign_agent_to_task.py` and `agents/sdk_bridge.py`.

### Verbatim Observations & Code Snippets

#### Observation 1.1: Consumer Expectations (`assign_agent_to_task.py` & `sdk_bridge.py`)
In `tools/assign_agent_to_task.py` (lines 25–27):
```python
agent_module = utils.load_module(f"agents/{agent_name}.py")
agent_function = getattr(agent_module, agent_name)
result = agent_function(task=task)
del sys.modules[agent_module.__name__]
response = result["messages"][-1].content
```
In `agents/sdk_bridge.py` (lines 115–117):
```python
agent_module = utils.load_module(f"agents/{agent_name}.py")
agent_function = getattr(agent_module, agent_name)
result = agent_function(task=task)
del sys.modules[agent_module.__name__]
response = result["messages"][-1].content
```
Both consumers invoke `agent_function(task=task)` and expect the returned `result` to be a dictionary (LangGraph state dict) containing a `"messages"` list key.

#### Observation 1.2: Current Entry Point Annotations in Target Files

1. **`agent_smith.py` (Line 135)**:
   ```python
   def agent_smith(task: str) -> str:
       """Designs and implements new agents, each designed to play a unique role."""
       return graph.invoke({"messages": [SystemMessage(system_prompt), HumanMessage(task)]})
   ```
   *Current return annotation:* `-> str` (Incorrect; `graph.invoke` returns `dict[str, Any]`).

2. **`software_engineer.py` (Line 69)**:
   ```python
   def software_engineer(task: str) -> str:
       """Creates, modifies, and deletes code, manages files, runs shell commands, and collaborates with other agents."""
       return graph.invoke(
           {"messages": [SystemMessage(system_prompt), HumanMessage(task)]}
       )
   ```
   *Current return annotation:* `-> str` (Incorrect; `graph.invoke` returns `dict[str, Any]`).

3. **`tool_maker.py` (Line 183)**:
   ```python
   def tool_maker(task: str, os_context: str | dict | None = None) -> str:
       """Creates new tools for agents to use."""
       prompt = build_tool_maker_prompt(os_context)
       return graph.invoke({"messages": [SystemMessage(prompt), HumanMessage(task)]})
   ```
   *Current return annotation:* `-> str` (Incorrect; `graph.invoke` returns `dict[str, Any]`).

4. **`web_researcher.py` (Line 57)**:
   ```python
   def web_researcher(task: str) -> str:
       """Researches the web."""
       return graph.invoke(
           {"messages": [SystemMessage(system_prompt), HumanMessage(task)]}
       )
   ```
   *Current return annotation:* `-> str` (Incorrect; `graph.invoke` returns `dict[str, Any]`).

#### Observation 1.3: Unannotated LangGraph Node Functions (`reasoning`)
In all 4 files, the internal node function `reasoning(state: MessagesState)` lacks a return type annotation:
- `agent_smith.py` (line 95): `def reasoning(state: MessagesState):` -> returns `{"messages": [response]}`
- `software_engineer.py` (line 32): `def reasoning(state: MessagesState):` -> returns `{"messages": [response]}`
- `tool_maker.py` (line 144): `def reasoning(state: MessagesState):` -> returns `{"messages": [response]}`
- `web_researcher.py` (line 20): `def reasoning(state: MessagesState):` -> returns `{"messages": [response]}`

#### Observation 1.4: Current Helper Functions
- `agent_smith.py`:
  - `load_agent_template(...) -> tuple[str, str]` (Line 15): correctly returns tuple of strings.
  - `get_system_prompt(...) -> str` (Line 32): correctly returns system prompt string.
- `tool_maker.py`:
  - `get_os_guidance_prompt(...) -> str` (Line 11): correctly returns OS guidance string.
  - `build_tool_maker_prompt(...) -> str` (Line 46): correctly returns full system prompt string.

#### Observation 1.5: Imports Analysis
All 4 target files currently import:
```python
from typing import Literal
```
None of the 4 files import `Any` from `typing`.

---

## 2. Logic Chain

1. **Premise**: In LangGraph, `StateGraph.compile().invoke(input_dict)` executes the graph and returns the final state dictionary (of type `dict[str, Any]` matching `MessagesState`).
2. **Observation Step 1.1**: Callers `assign_agent_to_task` and `sdk_bridge` rely on `agent_function` returning this state dict, indexing into `result["messages"][-1].content`.
3. **Observation Step 1.2**: All four agent entry points (`agent_smith`, `software_engineer`, `tool_maker`, `web_researcher`) execute `return graph.invoke(...)` and return state dictionaries, but their type annotations erroneously claim `-> str`.
4. **Impact Assessment**: Static type checkers (mypy/pyright) and IDE tools report type errors when callers index into `result["messages"]`, because `result` is inferred as `str`.
5. **Deduction**:
   - The entry points must be re-annotated as `-> dict[str, Any]`.
   - `Any` must be imported from `typing` (`from typing import Any, Literal`).
   - The node helper functions `reasoning(state: MessagesState)` should also be annotated as `-> dict[str, Any]` for consistency and type safety across all internal graph nodes.
   - Helper wrappers (`load_agent_template` -> `tuple[str, str]`, `get_system_prompt` -> `str`, `get_os_guidance_prompt` -> `str`, `build_tool_maker_prompt` -> `str`) already accurately reflect their string return types and require no changes.

---

## 3. Caveats

- **Runtime Execution**: Runtime behavior is unaffected by type annotation fixes because `graph.invoke(...)` has always returned `dict[str, Any]`.
- **System Prompt Formatting Artifact**: `web_researcher.py` line 12 contains a verbatim triple-backtick artifact inside the prompt docstring (` ``` `). This does not break execution but is a minor formatting defect.
- **Import Placement in `software_engineer.py`**: Imports of tools in `software_engineer.py` (lines 14–20) occur mid-file after `system_prompt`. This functions properly, but moving tool imports to top of file follows standard PEP8 conventions.

---

## 4. Conclusion

All 4 agent entry point functions (`agent_smith`, `software_engineer`, `tool_maker`, `web_researcher`) currently suffer from inaccurate return type annotations (`-> str` instead of `-> dict[str, Any]`). 

### Recommended Exact Refactorings

#### 1. Refactoring `/Users/ricardo/AgentK/agents/agent_smith.py`

**Line 2:**
```python
# Before
from typing import Literal

# After
from typing import Any, Literal
```

**Lines 95–101:**
```python
# Before
def reasoning(state: MessagesState):
    print()
    print("agent_smith is thinking...")
    messages = state["messages"]
    tooled_up_model = config.default_langchain_model.bind_tools(tools)
    response = tooled_up_model.invoke(messages)
    return {"messages": [response]}

# After
def reasoning(state: MessagesState) -> dict[str, Any]:
    print()
    print("agent_smith is thinking...")
    messages = state["messages"]
    tooled_up_model = config.default_langchain_model.bind_tools(tools)
    response = tooled_up_model.invoke(messages)
    return {"messages": [response]}
```

**Lines 135–137:**
```python
# Before
def agent_smith(task: str) -> str:
    """Designs and implements new agents, each designed to play a unique role."""
    return graph.invoke({"messages": [SystemMessage(system_prompt), HumanMessage(task)]})

# After
def agent_smith(task: str) -> dict[str, Any]:
    """Designs and implements new agents, each designed to play a unique role."""
    return graph.invoke({"messages": [SystemMessage(system_prompt), HumanMessage(task)]})
```

---

#### 2. Refactoring `/Users/ricardo/AgentK/agents/software_engineer.py`

**Line 1:**
```python
# Before
from typing import Literal

# After
from typing import Any, Literal
```

**Lines 32–37:**
```python
# Before
def reasoning(state: MessagesState):
    print("software_engineer is thinking...")
    messages = state['messages']
    tooled_up_model = config.default_langchain_model.bind_tools(tools)
    response = tooled_up_model.invoke(messages)
    return {"messages": [response]}

# After
def reasoning(state: MessagesState) -> dict[str, Any]:
    print("software_engineer is thinking...")
    messages = state['messages']
    tooled_up_model = config.default_langchain_model.bind_tools(tools)
    response = tooled_up_model.invoke(messages)
    return {"messages": [response]}
```

**Lines 69–73:**
```python
# Before
def software_engineer(task: str) -> str:
    """Creates, modifies, and deletes code, manages files, runs shell commands, and collaborates with other agents."""
    return graph.invoke(
        {"messages": [SystemMessage(system_prompt), HumanMessage(task)]}
    )

# After
def software_engineer(task: str) -> dict[str, Any]:
    """Creates, modifies, and deletes code, manages files, runs shell commands, and collaborates with other agents."""
    return graph.invoke(
        {"messages": [SystemMessage(system_prompt), HumanMessage(task)]}
    )
```

---

#### 3. Refactoring `/Users/ricardo/AgentK/agents/tool_maker.py`

**Line 1:**
```python
# Before
from typing import Literal

# After
from typing import Any, Literal
```

**Lines 144–150:**
```python
# Before
def reasoning(state: MessagesState):
    print()
    print("tool_maker is thinking...")
    messages = state["messages"]
    tooled_up_model = config.default_langchain_model.bind_tools(tools)
    response = tooled_up_model.invoke(messages)
    return {"messages": [response]}

# After
def reasoning(state: MessagesState) -> dict[str, Any]:
    print()
    print("tool_maker is thinking...")
    messages = state["messages"]
    tooled_up_model = config.default_langchain_model.bind_tools(tools)
    response = tooled_up_model.invoke(messages)
    return {"messages": [response]}
```

**Lines 183–186:**
```python
# Before
def tool_maker(task: str, os_context: str | dict | None = None) -> str:
    """Creates new tools for agents to use."""
    prompt = build_tool_maker_prompt(os_context)
    return graph.invoke({"messages": [SystemMessage(prompt), HumanMessage(task)]})

# After
def tool_maker(task: str, os_context: str | dict | None = None) -> dict[str, Any]:
    """Creates new tools for agents to use."""
    prompt = build_tool_maker_prompt(os_context)
    return graph.invoke({"messages": [SystemMessage(prompt), HumanMessage(task)]})
```

---

#### 4. Refactoring `/Users/ricardo/AgentK/agents/web_researcher.py`

**Line 1:**
```python
# Before
from typing import Literal

# After
from typing import Any, Literal
```

**Lines 20–25:**
```python
# Before
def reasoning(state: MessagesState):
    print("web_researcher is thinking...")
    messages = state['messages']
    tooled_up_model = config.default_langchain_model.bind_tools(tools)
    response = tooled_up_model.invoke(messages)
    return {"messages": [response]}

# After
def reasoning(state: MessagesState) -> dict[str, Any]:
    print("web_researcher is thinking...")
    messages = state['messages']
    tooled_up_model = config.default_langchain_model.bind_tools(tools)
    response = tooled_up_model.invoke(messages)
    return {"messages": [response]}
```

**Lines 57–61:**
```python
# Before
def web_researcher(task: str) -> str:
    """Researches the web."""
    return graph.invoke(
        {"messages": [SystemMessage(system_prompt), HumanMessage(task)]}
    )

# After
def web_researcher(task: str) -> dict[str, Any]:
    """Researches the web."""
    return graph.invoke(
        {"messages": [SystemMessage(system_prompt), HumanMessage(task)]}
    )
```

---

## 5. Verification Method

To verify these findings and test the refactorings independently:

1. Run agent unit test suite:
   ```bash
   OPENAI_API_KEY=mock-key PYTHONPATH=. python3 -m unittest discover tests/agents
   ```
2. Verify return type annotations using Python AST / inspection:
   ```bash
   python3 -c "import typing, agents.agent_smith, agents.software_engineer, agents.tool_maker, agents.web_researcher; print(typing.get_type_hints(agents.agent_smith.agent_smith)); print(typing.get_type_hints(agents.software_engineer.software_engineer)); print(typing.get_type_hints(agents.tool_maker.tool_maker)); print(typing.get_type_hints(agents.web_researcher.web_researcher))"
   ```
   *Expected output after refactoring:* Each entry point function returns `dict[str, typing.Any]`.

3. Invalidation condition:
   If any agent entry point function is modified to extract and return a plain string (e.g. `response["messages"][-1].content`), then the type annotation `-> str` would become valid, but consumer callers `assign_agent_to_task.py` and `sdk_bridge.py` would break when trying to execute `result["messages"]`. Therefore, `-> dict[str, Any]` is strictly required as long as entry points return `graph.invoke(...)`.
