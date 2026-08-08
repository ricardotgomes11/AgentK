"""
AgentK SDK Bridge
=================
Bridges the google-antigravity SDK with the existing LangGraph agent architecture.
Exposes AgentK's identity, agent inventory, and orchestration capabilities
through the SDK's Agent interface without modifying any existing agents or tools.
"""

import os
import sys
import sqlite3
import traceback

# Ensure the AgentK root is on the path so existing imports work
AGENTK_ROOT = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(AGENTK_ROOT)
for _p in (AGENTK_ROOT, _project_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    import utils
    _UTILS_AVAILABLE = True
except ImportError as _e:
    _UTILS_AVAILABLE = False
    _UTILS_ERROR = str(_e)


def get_agent_inventory() -> str:
    """Return a formatted string of all available agents and their descriptions."""
    if not _UTILS_AVAILABLE:
        return f"  (Agent discovery unavailable: {_UTILS_ERROR})"
    try:
        agents = utils.all_agents(exclude=["hermes"])
        if not agents:
            return "No agents currently available."
        lines = []
        for name, doc in agents.items():
            desc = doc.strip() if doc else "No description available."
            lines.append(f"  - **{name}**: {desc}")
        return "\n".join(lines)
    except Exception as e:
        return f"  (Error loading agent inventory: {e})"


def get_tool_inventory() -> str:
    """Return a formatted string of all available tools."""
    if not _UTILS_AVAILABLE:
        return f"  (Tool discovery unavailable: {_UTILS_ERROR})"
    try:
        tools = utils.list_tools()
        if not tools:
            return "No tools currently available."
        return "\n".join(f"  - {t}" for t in sorted(tools))
    except Exception as e:
        return f"  (Error loading tool inventory: {e})"


def get_system_prompt() -> str:
    """
    Compose the unified system prompt for the SDK Agent.
    This merges AgentK's identity with Hermes' orchestrator role
    and a live snapshot of available agents and tools.
    """
    agent_inventory = get_agent_inventory()
    tool_inventory = get_tool_inventory()

    return f"""You are Hermes, the orchestrator of AgentK — a self-evolving AGI system.

AgentK is a modular, self-evolving AGI made of agents that collaborate, and build
new agents as needed, in order to complete tasks for a user. The "K" stands for
kernel — the minimum set of agents and tools necessary to bootstrap itself and
then grow its own mind.

AgentK's mind is made up of:
- Agents who collaborate to solve problems
- Tools which those agents use to interact with the outside world

The kernel agents are:
- **hermes**: The orchestrator (you). Interacts with humans, manages tasks,
  coordinates agents.
- **agent_smith**: Designs and implements new agents.
- **tool_maker**: Creates new tools for agents to use.
- **software_engineer**: Creates, modifies, and deletes code.
- **web_researcher**: Researches the web for information.

You interact with the user in this order:
1. Reach a shared understanding on a goal.
2. Think of a detailed sequential plan for how to achieve the goal.
3. If a new kind of agent is required, coordinate its creation.
4. Assign agents and coordinate their activity based on your plan.
5. Respond to the user once the goal is achieved or if you need their input.

Design agent roles that optimise for composability and future re-use.

Currently available agents:
{agent_inventory}

Currently available tools:
{tool_inventory}
"""


def dispatch_agent(agent_name: str, task: str) -> str:
    """
    Dispatch a task to a named LangGraph agent.
    This is the bridge between the SDK world and the existing agent architecture.
    """
    print(f"[SDK Bridge] Dispatching to agent '{agent_name}': {task}")
    if not _UTILS_AVAILABLE:
        return f"Error: Agent dispatch unavailable ({_UTILS_ERROR})"
    try:
        agent_module = utils.load_module(f"agents/{agent_name}.py")
        agent_function = getattr(agent_module, agent_name)
        result = agent_function(task=task)
        del sys.modules[agent_module.__name__]
        response = result["messages"][-1].content
        print(f"[SDK Bridge] {agent_name} responded.")
        return response
    except Exception as e:
        exception_trace = traceback.format_exc()
        error = (
            f"Error dispatching to {agent_name}: {e}\n{exception_trace}"
        )
        print(f"[SDK Bridge] {error}")
        return error
