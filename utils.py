import sqlite3
import importlib.util
import sys
import string
import secrets
import traceback
import os
import platform
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    conn = sqlite3.connect(str(PROJECT_ROOT / "checkpoints.sqlite"), check_same_thread=False)
    checkpointer = SqliteSaver(conn)
except Exception:
    try:
        from langgraph_checkpoint_sqlite import SqliteSaver
        conn = sqlite3.connect(str(PROJECT_ROOT / "checkpoints.sqlite"), check_same_thread=False)
        checkpointer = SqliteSaver(conn)
    except Exception:
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()


def get_platform_info() -> dict:
    """Detect current OS platform, system version, and available package manager."""
    system_name = platform.system()  # 'Darwin', 'Linux', 'Windows'

    pkg_manager = None
    pkg_list_file = None

    if system_name == "Darwin":
        os_display = f"macOS {platform.mac_ver()[0]}"
        if shutil.which("brew"):
            pkg_manager = "brew"
            pkg_list_file = "brew-packages-list.txt"
    elif system_name == "Linux":
        os_display = f"Linux ({platform.release()})"
        if shutil.which("apt-get"):
            pkg_manager = "apt-get"
            pkg_list_file = "apt-packages-list.txt"
        elif shutil.which("dnf"):
            pkg_manager = "dnf"
            pkg_list_file = "dnf-packages-list.txt"
        elif shutil.which("pacman"):
            pkg_manager = "pacman"
            pkg_list_file = "pacman-packages-list.txt"
        elif shutil.which("apk"):
            pkg_manager = "apk"
            pkg_list_file = "apk-packages-list.txt"
    else:
        os_display = f"{system_name} {platform.release()}"

    return {
        "system": system_name,
        "os_display": os_display,
        "pkg_manager": pkg_manager,
        "pkg_list_file": pkg_list_file,
    }


def all_tool_functions():
    tools = list_tools()
    tool_funcs = []

    for tool in tools:
        try:
            tool_path = PROJECT_ROOT / "tools" / f"{tool}.py"
            source = str(tool_path) if tool_path.exists() else f"tools/{tool}.py"
            module = load_module(source)
            tool_func = getattr(module, tool)
            tool_funcs.append(tool_func)
        except Exception as e:
            print(f'WARN: Could not load tool "{tool}". {e.__class__.__name__}: {e}')

    return tool_funcs


def list_broken_tools():
    tools = list_tools()
    broken_tools = {}

    for tool in tools:
        try:
            tool_path = PROJECT_ROOT / "tools" / f"{tool}.py"
            source = str(tool_path) if tool_path.exists() else f"tools/{tool}.py"
            module = load_module(source)
            getattr(module, tool)
            del sys.modules[module.__name__]
        except Exception as e:
            exception_trace = traceback.format_exc()
            broken_tools[tool] = [e, exception_trace]

    return broken_tools


def list_tools():
    """
    list all tools available in the tools directory

    :return: list of tools
    """
    tools = []
    tools_dir = PROJECT_ROOT / "tools"
    target_dir = str(tools_dir) if tools_dir.exists() else "tools"
    for file in os.listdir(target_dir):
        if file.endswith(".py") and not file.startswith("__"):
            tools.append(file[:-3])

    return tools


def all_agents(exclude=["hermes"]):
    agents = list_agents()
    agents = [agent for agent in agents if agent not in exclude]
    agent_funcs = {}

    for agent in agents:
        try:
            agent_path = PROJECT_ROOT / "agents" / f"{agent}.py"
            source = str(agent_path) if agent_path.exists() else f"agents/{agent}.py"
            module = load_module(source)
            agent_func = getattr(module, agent)
            agent_funcs[agent] = agent_func.__doc__
            del sys.modules[module.__name__]
        except Exception as e:
            print(f'WARN: Could not load agent "{agent}". {e.__class__.__name__}: {e}')

    return agent_funcs


def list_broken_agents():
    agents = list_agents()
    broken_agents = {}

    for agent in agents:
        try:
            agent_path = PROJECT_ROOT / "agents" / f"{agent}.py"
            source = str(agent_path) if agent_path.exists() else f"agents/{agent}.py"
            module = load_module(source)
            getattr(module, agent)
            del sys.modules[module.__name__]
        except Exception as e:
            exception_trace = traceback.format_exc()
            broken_agents[agent] = [e, exception_trace]

    return broken_agents


def list_agents():
    """
    list all agents available in the agents directory

    :return: list of agents
    """
    agents = []
    agents_dir = PROJECT_ROOT / "agents"
    target_dir = str(agents_dir) if agents_dir.exists() else "agents"
    for file in os.listdir(target_dir):
        if file.endswith(".py") and file != "__init__.py":
            agents.append(file[:-3])

    return agents


def gensym(length=32, prefix="gensym_"):
    """
    generates a fairly unique symbol, used to make a module name,
    used as a helper function for load_module

    :return: generated symbol
    """
    alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits
    symbol = "".join([secrets.choice(alphabet) for i in range(length)])

    return prefix + symbol


def load_module(source, module_name=None):
    """
    reads file source and loads it as a module

    :param source: file to load
    :param module_name: name of module to register in sys.modules
    :return: loaded module
    """

    if module_name is None:
        module_name = gensym()

    spec = importlib.util.spec_from_file_location(module_name, source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return module