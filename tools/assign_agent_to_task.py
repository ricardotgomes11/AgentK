import sys
import traceback
from langchain_core.tools import tool
import utils

# Track recursion depth globally to prevent agent fork bombs
_recursion_depth = 0
MAX_DEPTH = 3

@tool
def assign_agent_to_task(agent_name: str, task: str):
    """Assign an agent to a task. This function returns the response from the agent."""
    global _recursion_depth
    print(f"Assigning agent {agent_name} to task: {task} (depth: {_recursion_depth})")
    
    if _recursion_depth >= MAX_DEPTH:
        error = f"Error: Agent assignment recursion limit ({MAX_DEPTH}) reached. Blocking assignment to prevent fork bomb."
        print(error)
        return error
        
    _recursion_depth += 1
    try:
        agent_module = utils.load_module(f"agents/{agent_name}.py")
        agent_function = getattr(agent_module, agent_name)
        result = agent_function(task=task)
        del sys.modules[agent_module.__name__]
        response = result["messages"][-1].content
        print(f"{agent_name} responded:")
        print(response)
        return response
    except Exception as e:
        exception_trace = traceback.format_exc()
        error = f"An error occurred while assigning {agent_name} to task {task}:\n {e}\n{exception_trace}"
        print(error)
        return error
    finally:
        _recursion_depth -= 1