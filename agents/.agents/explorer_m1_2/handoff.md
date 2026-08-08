# Handoff Report — Explorer 2: Milestone 1 (Control Plane & Path Portability)

## 1. Observation

### Source File Analysis (`/Users/ricardo/AgentK/agents/agent_smith.py`)
In `/Users/ricardo/AgentK/agents/agent_smith.py`, lines 10–16 read as follows:

```python
example_agent = "web_researcher"

with open(f"agents/{example_agent}.py", 'r') as file:
    agent_code = file.read()
    
with open(f"tests/agents/test_{example_agent}.py", 'r') as file:
    agent_test_code = file.read()
```

- **Line 12**: `with open(f"agents/{example_agent}.py", 'r') as file:` uses string relative path `"agents/web_researcher.py"`.
- **Line 15**: `with open(f"tests/agents/test_{example_agent}.py", 'r') as file:` uses string relative path `"tests/agents/test_web_researcher.py"`.
- Both file openings are executed at **module import time** (top-level scope).
- Neither file opening uses `__file__` or `pathlib.Path` resolution.

### Error Reproduction
Running Python with a CWD other than the repository root (`/Users/ricardo/AgentK`), e.g.:
```bash
python3 -c "import os; os.chdir('/tmp'); import agents.agent_smith"
```
Produces verbatim exception:
```
FileNotFoundError: [Errno 2] No such file or directory: 'agents/web_researcher.py'
```

### Test File Status (`/Users/ricardo/AgentK/tests/agents/test_agent_smith.py`)
- `/Users/ricardo/AgentK/tests/agents/test_agent_smith.py` does **not exist** currently in the workspace.

### Secondary / Indirect Path Dependencies
- Line 67: `{utils.all_agents(exclude=["hermes", "agent_smith"])}`
- Line 70: `tools = utils.all_tool_functions()`
- Both functions in `utils.py` execute `os.listdir("agents")` and `os.listdir("tools")` using CWD-relative string paths.

---

## 2. Logic Chain

1. **Observation**: Lines 12 and 15 in `agents/agent_smith.py` pass relative string paths (`"agents/web_researcher.py"` and `"tests/agents/test_web_researcher.py"`) to Python's built-in `open()` function.
2. **Step 1**: In Python, relative file paths passed to `open()` are evaluated relative to `os.getcwd()` (the process's current working directory), rather than relative to the directory containing `agent_smith.py`.
3. **Step 2**: When `agents/agent_smith.py` is imported or executed from any working directory other than `/Users/ricardo/AgentK` (e.g. `/tmp` or a subfolder), `os.getcwd()` is not the repository root. `open()` fails to locate `agents/web_researcher.py` and raises `FileNotFoundError`.
4. **Step 3**: Because these `open()` calls occur at top-level module load time, importing `agents.agent_smith` crashes immediately before any function inside the module can execute.
5. **Step 4**: `agent_smith.py` resides at `<REPO_ROOT>/agents/agent_smith.py`. Resolving `Path(__file__).resolve().parent.parent` reliably yields `<REPO_ROOT>` (`BASE_DIR`) regardless of `os.getcwd()`.
6. **Step 5**: Constructing target paths via `BASE_DIR / "agents" / f"{example_agent}.py"` and `BASE_DIR / "tests" / "agents" / f"test_{example_agent}.py"` guarantees absolute path resolution rooted at the AgentK directory.
7. **Step 6**: Encapsulating template loading and prompt construction into helper functions (`load_agent_template` and `get_system_prompt`) enables top-level export of `system_prompt` while allowing isolated, deterministic unit testing of template loading and CWD independence.

---

## 3. Caveats

1. **`utils.py` Dependency**: `agent_smith.py` calls `utils.all_agents()` and `utils.all_tool_functions()`. `utils.py` contains relative `os.listdir("agents")` and `os.listdir("tools")` calls. Full CWD independence of `agent_smith.py` when loaded end-to-end also requires `utils.py` path refactoring (handled in Explorer 1 scope).
2. **LangChain / LLM Execution in Tests**: Invoking `agent_smith(task)` triggers `config.default_langchain_model.bind_tools(tools)`, requiring active model configurations or API keys. Unit tests for `test_agent_smith.py` must mock model calls or focus on testing pure functions (`load_agent_template`, `get_system_prompt`, `check_for_tool_calls`).

---

## 4. Conclusion & Actionable Refactoring Instructions

### 4.1 Refactoring Plan for `/Users/ricardo/AgentK/agents/agent_smith.py`

Replace top-level direct file openings with `Path(__file__)` anchor resolution and helper functions:

```python
from pathlib import Path
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode

import config
import utils

# Project root directory anchor
BASE_DIR = Path(__file__).resolve().parent.parent

def load_agent_template(example_agent: str = "web_researcher", base_dir: Path | None = None) -> tuple[str, str]:
    """Loads source and test template code for a given example agent relative to base_dir."""
    if base_dir is None:
        base_dir = BASE_DIR
        
    agent_path = base_dir / "agents" / f"{example_agent}.py"
    test_path = base_dir / "tests" / "agents" / f"test_{example_agent}.py"
    
    with open(agent_path, 'r', encoding='utf-8') as file:
        agent_code = file.read()
        
    with open(test_path, 'r', encoding='utf-8') as file:
        agent_test_code = file.read()
        
    return agent_code, agent_test_code

def get_system_prompt(example_agent: str = "web_researcher", base_dir: Path | None = None) -> str:
    """Constructs the system prompt for agent_smith with CWD-independent template loading."""
    agent_code, agent_test_code = load_agent_template(example_agent, base_dir=base_dir)
    
    return f"""You are agent_smith, a ReAct agent that develops other ReAct agents.

You are part of a system called AgentK - an autoagentic AGI.
AgentK is a self-evolving AGI made of agents that collaborate, and build new agents as needed, in order to complete tasks for a user.
Agent K is a modular, self-evolving AGI system that gradually builds its own mind as you challenge it to complete tasks.
The "K" stands kernel, meaning small core. The aim is for AgentK to be the minimum set of agents and tools necessary for it to bootstrap itself and then grow its own mind.

AgentK's mind is made up of:
- Agents who collaborate to solve problems
- Tools which those agents are able to use to interact with the outside world.

Your responses must be either an inner monologue or a message to the user.
If you are intending to call tools, then your response must be a succinct summary of your inner thoughts.
Else, your response is a message the user.

You approach your given task this way:
1. Create a detailed plan for how to design an agent to achieve the task.
2. If new tools are required, assign tasks to the tool_maker agent.
3. Write the agent implementation and a smoke test to disk.
4. Verify the smoke test doesn't error.
5. Confirm the agent is complete with its name and a succinct description of its purpose.

Further guidance:

All agents MUST go in the `agents` directory.
All tools MUST go in the `tools` directory.
New agents MUST import their tools from the `tools` directory like this: `from tools.tool_name import tool_name`.
The name of the agent file and the agent function must be the same.
You develop agents in python using LangGraph to define their flow.
You design agents with the tools they potentially need to complete their tasks.
If a certain kind of tool should be supplied to an agent but it doesn't exist, assign the tool_maker agent to create that new tool.
Assign tool_maker a task for each tool that needs to be created.
Always include a test file that smoke tests the agent.
Use write_to_file tool to write the tool and test to disk.
You MUST always run the smoke test and ensure it doesn't error before considering the agent complete.
Avoid creating agents that are simply proxies for invoking a function with no additional reasoning; this is usually a sign that the agent is too specific and should be more generalised.

Example:
agents/{example_agent}.py
```
{agent_code}
```

tests/agents/test_{example_agent}.py
```
{agent_test_code}
```

Here's a list of currently available agents:
{utils.all_agents(exclude=["hermes", "agent_smith"])}
"""

example_agent = "web_researcher"
system_prompt = get_system_prompt(example_agent)

tools = utils.all_tool_functions()

def reasoning(state: MessagesState):
    print()
    print("agent_smith is thinking...")
    messages = state['messages']
    tooled_up_model = config.default_langchain_model.bind_tools(tools)
    response = tooled_up_model.invoke(messages)
    return {"messages": [response]}

def check_for_tool_calls(state: MessagesState) -> Literal["tools", END]:
    messages = state['messages']
    last_message = messages[-1]
    
    if last_message.tool_calls:
        if not last_message.content.strip() == "":
            print("agent_smith thought this:")
            print(last_message.content)
        print()
        print("agent_smith is acting by invoking these tools:")
        print([tool_call["name"] for tool_call in last_message.tool_calls])
        return "tools"
    
    return END

acting = ToolNode(tools)

workflow = StateGraph(MessagesState)
workflow.add_node("reasoning", reasoning)
workflow.add_node("tools", acting)
workflow.set_entry_point("reasoning")
workflow.add_conditional_edges(
    "reasoning",
    check_for_tool_calls,
)
workflow.add_edge("tools", 'reasoning')

graph = workflow.compile()

def agent_smith(task: str) -> str:
    """Designs and implements new agents, each designed to play a unique role."""
    return graph.invoke(
        {"messages": [SystemMessage(system_prompt), HumanMessage(task)]}
    )
```

### 4.2 Implementation Specification for `/Users/ricardo/AgentK/tests/agents/test_agent_smith.py`

Create `/Users/ricardo/AgentK/tests/agents/test_agent_smith.py` with the following test coverage:

1. **Callable Interface**: Verify `agent_smith` function and `graph` object exist and are callable.
2. **Template Loading**: Verify `load_agent_template("web_researcher")` returns valid source code and test code.
3. **System Prompt Construction**: Verify `get_system_prompt()` properly embeds template code into prompt blocks.
4. **CWD Independence**: Execute template loading and prompt construction inside `os.chdir(tmp_dir)` to ensure complete immunity to process CWD.
5. **Graph Logic Routing**: Unit test `check_for_tool_calls` with mock messages containing tool calls vs empty tool calls.

```python
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from agents.agent_smith import (
    BASE_DIR,
    agent_smith,
    check_for_tool_calls,
    get_system_prompt,
    graph,
    load_agent_template,
)


class TestAgentSmith(unittest.TestCase):
    def test_callable_interface(self):
        """Verify that agent_smith function and graph are defined and callable."""
        self.assertTrue(callable(agent_smith))
        self.assertIsNotNone(graph)

    def test_load_agent_template(self):
        """Test loading template files using base_dir resolution."""
        agent_code, test_code = load_agent_template("web_researcher")
        self.assertIn("def web_researcher", agent_code)
        self.assertIn("TestWebResearcher", test_code)

    def test_get_system_prompt(self):
        """Test system prompt construction with template injection."""
        prompt = get_system_prompt("web_researcher")
        self.assertIn("You are agent_smith", prompt)
        self.assertIn("def web_researcher", prompt)
        self.assertIn("TestWebResearcher", prompt)

    def test_cwd_independence(self):
        """Verify template loading succeeds regardless of process CWD."""
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                os.chdir(tmp_dir)
                agent_code, test_code = load_agent_template("web_researcher")
                self.assertIn("def web_researcher", agent_code)
                prompt = get_system_prompt("web_researcher")
                self.assertIn("agent_smith", prompt)
            finally:
                os.chdir(original_cwd)

    def test_check_for_tool_calls_routing(self):
        """Test StateGraph routing logic for tool calls vs END."""
        mock_msg_with_tools = MagicMock()
        mock_msg_with_tools.tool_calls = [{"name": "write_to_file", "args": {}}]
        mock_msg_with_tools.content = "I will write a file"
        
        result_tools = check_for_tool_calls({"messages": [mock_msg_with_tools]})
        self.assertEqual(result_tools, "tools")

        mock_msg_no_tools = MagicMock()
        mock_msg_no_tools.tool_calls = []
        mock_msg_no_tools.content = "Done"
        
        result_end = check_for_tool_calls({"messages": [mock_msg_no_tools]})
        self.assertEqual(result_end, "__end__")


if __name__ == '__main__':
    unittest.main()
```

---

## 5. Verification Method

### 5.1 Verification Commands
1. **CWD Independence Verification**:
   ```bash
   PYTHONPATH=. python3 -c "import os; os.chdir('/tmp'); from agents.agent_smith import get_system_prompt; print('Prompt length:', len(get_system_prompt()))"
   ```
   *Expected Result*: Output `Prompt length: <int>` without raising `FileNotFoundError`.

2. **Unit Test Execution**:
   ```bash
   PYTHONPATH=. python3 -m unittest tests/agents/test_agent_smith.py
   ```
   *Expected Result*: `OK (5 tests)`

### 5.2 Invalidation Conditions
- Any occurrence of string literals passed to `open()` without `BASE_DIR` or `Path(__file__)` anchoring.
- `FileNotFoundError` raised when importing or invoking template loading from `/tmp` or non-root directories.
