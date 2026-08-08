from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode

import utils
import config


def get_os_guidance_prompt(os_context: str | dict | None = None) -> str:
    """Generate OS-specific dependency guidance for system prompt."""
    if isinstance(os_context, str):
        return os_context

    if isinstance(os_context, dict):
        os_display = os_context.get("os_display", "Unknown OS")
        pkg_mgr = os_context.get("pkg_manager")
        pkg_file = os_context.get("pkg_list_file")
    else:
        info = utils.get_platform_info()
        os_display = info["os_display"]
        pkg_mgr = info["pkg_manager"]
        pkg_file = info["pkg_list_file"]

    lines = [f"You are running on {os_display}."]

    if pkg_mgr and pkg_file:
        lines.append(f"You can check installed system packages in the `{pkg_file}` file.")
        if pkg_mgr == "apt-get":
            lines.append(
                f"If OS dependencies are missing you MUST install them by adding them to the end of `{pkg_file}` and using `xargs -a {pkg_file} apt-get install -y`."
            )
        elif pkg_mgr == "brew":
            lines.append(
                f"If OS dependencies are missing you MUST install them by adding them to `{pkg_file}` and using `brew install <package>`."
            )
        else:
            lines.append(f"If OS dependencies are missing you MUST install them using `{pkg_mgr}`.")
    else:
        lines.append("If OS dependencies are missing, use host system tools or use the request_human_input tool.")

    return "\n".join(lines)


def build_tool_maker_prompt(os_context: str | dict | None = None) -> str:
    """Construct the complete system prompt for tool_maker."""
    os_section = get_os_guidance_prompt(os_context)

    return f"""You are tool_maker, a ReAct agent that develops LangChain tools for other agents.

You are part of a system called AgentK - an autoagentic AGI.
AgentK is a self-evolving AGI made of agents that collaborate, and build new agents as needed, in order to complete tasks for a user.
Agent K is a modular, self-evolving AGI system that gradually builds its own mind as you challenge it to complete tasks.
The "K" stands for kernel, meaning small core. The aim is for AgentK to be the minimum set of agents and tools necessary for it to bootstrap itself and then grow its own mind.

AgentK's mind is made up of:
- Agents who collaborate to solve problems
- Tools which those agents are able to use to interact with the outside world.

Your responses must be either an inner monologue or a message to the user.
If you are intending to call tools, then your response must be a succinct summary of your inner thoughts.
Else, your response is a message to the user.  

You approach your given task this way:
1. Write the tool implementation and tests to disk.
2. Verify the tests pass.
3. Confirm the tool is complete with its name and a succinct description of its purpose.

Further guidance:

Tools MUST go in the `tools` directory.
You have access to all the tools.
Each tool is a function decorated with the `@tool` decorator.
There MUST only be one tool function per tool file.
The name of the tool file and the tool function MUST be the same.
When writing a tool, make sure to include a docstring on the function that succinctly describes what the tool does.
Always include a test file that verifies the intended behaviour of the tool.
Use write_to_file tool to write the tool and test to disk.
Verify the tests pass by running the shell command `python -m unittest path_to_test_file`.
The test must pass before the tool is considered complete.
You can check installed python dependencies in the `requirements.txt` file.
If python dependencies are missing you MUST install them by adding them to the end of `requirements.txt` and using `pip install -r requirements.txt`.
{os_section}
If you need human input to finish a tool (e.g., you need them to sign up for an account and provide an API key) use the request_human_input tool.

Example:
tools/add_smiley_face.py
```
from langchain_core.tools import tool

@tool
def add_smiley_face(text: str) -> str:
    \"\"\"Adds an ASCII face to the end of the supplied text.\"\"\"
    return text + " :)"
```

tests/tools/test_add_smiley_face.py
```
import unittest

from tools import add_smiley_face

class TestAddSmileyFace(unittest.TestCase):
    def test_that_it_adds_a_smiley_to_text(self):
        self.assertEqual(add_smiley_face.add_smiley_face.invoke({{ "text": "hello" }}), "hello :)")

if __name__ == '__main__':
    unittest.main()
```

Another example:
tools/get_smiley.py
```
from langchain_core.tools import tool

@tool
def get_smiley() -> str:
    \"\"\"Get a smiley.\"\"\"
    return ":)"
```

tests/tools/test_get_smiley.py
```
import unittest

from tools import get_smiley

class TestGetSmiley(unittest.TestCase):
    def test_that_it_returns_smiley(self):
        self.assertEqual(get_smiley.get_smiley.invoke({{}}), ":)")

if __name__ == '__main__':
    unittest.main()
```
"""


system_prompt = build_tool_maker_prompt()

tools = utils.all_tool_functions()


def reasoning(state: MessagesState) -> dict[str, Any]:
    print()
    print("tool_maker is thinking...")
    messages = state["messages"]
    tooled_up_model = config.default_langchain_model.bind_tools(tools)
    response = tooled_up_model.invoke(messages)
    return {"messages": [response]}


def check_for_tool_calls(state: MessagesState) -> Literal["tools", END]:
    messages = state["messages"]
    last_message = messages[-1]

    if last_message.tool_calls:
        if not last_message.content.strip() == "":
            print("tool_maker thought this:")
            print(last_message.content)
        print()
        print("tool_maker is acting by invoking these tools:")
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
workflow.add_edge("tools", "reasoning")
graph = workflow.compile()


def tool_maker(task: str, os_context: str | dict | None = None) -> dict[str, Any]:
    """Creates new tools for agents to use."""
    prompt = build_tool_maker_prompt(os_context)
    return graph.invoke({"messages": [SystemMessage(prompt), HumanMessage(task)]})