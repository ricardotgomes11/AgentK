# Handoff Report: Control Plane & Path Portability (tool_maker.py & System Prompt OS Specs)

**Agent**: Explorer 3 (Milestone 1)  
**Working Directory**: `/Users/ricardo/AgentK/agents/.agents/explorer_m1_3`  
**Date**: 2026-07-25  

---

## 1. Observation

### 1.1 Hardcoded OS Specs in `agents/tool_maker.py`
Direct inspection of `/Users/ricardo/AgentK/agents/tool_maker.py` reveals static hardcoded OS identity and Linux/Debian package manager commands inside the module-level `system_prompt` string (lines 10–98):

- **Line 44**: `"You are running on Debian 11."`
- **Line 45**: `"You can check installed debian packages in the `apt-packages-list.txt` file."`
- **Line 46**: `"If OS dependencies are missing you MUST install them by adding them to the end of `apt-packages-list.txt` and using `xargs -a apt-packages-list.txt apt-get install -y`."`

Furthermore, lines 139–143 define the function entry point:
```python
def tool_maker(task: str) -> str:
    """Creates new tools for agents to use."""
    return graph.invoke(
        {"messages": [SystemMessage(system_prompt), HumanMessage(task)]}
    )
```
The static `system_prompt` is unconditionally passed to `SystemMessage(system_prompt)`, preventing any runtime configuration or adaptation based on the execution environment.

### 1.2 System Environment & Related Files
- `/Users/ricardo/AgentK/apt-packages-list.txt` exists at project root and specifies 7 Debian APT packages:
  ```text
  wget
  curl
  git
  chromium-driver
  ca-certificates
  cmake
  libclang-dev
  ```
- `/Users/ricardo/AgentK/Dockerfile` hardcodes Debian package installation in lines 8–10:
  ```dockerfile
  COPY apt-packages-list.txt /tmp/apt-packages-list.txt
  RUN sed -i 's/\r$//' apt-packages-list.txt
  RUN xargs -a apt-packages-list.txt apt-get install -y
  ```

### 1.3 Inspection of `tests/` Conventions & Utilities
Inspection of `/Users/ricardo/AgentK/tests/` and subdirectories revealed:
- **Test Framework**: Standard library `unittest.TestCase`.
- **Directory Layout**:
  - `tests/agents/`: Agent smoke tests (e.g., `test_software_engineer.py`, `test_web_researcher.py`).
  - `tests/tools/`: Tool unit tests (e.g., `test_read_file.py`, `test_delete_file.py`, `test_overwrite_file.py`, `test_fetch_web_page_raw_html.py`, `test_request_human_input.py`).
- **Main Execution Guard**: Every test file ends with:
  ```python
  if __name__ == '__main__':
      unittest.main()
  ```
- **Test Runner Command**: Prompts instruct agents to verify tests via `python -m unittest path_to_test_file`.
- **Pytest Compatibility**: Bytecode cache in `tests/agents/__pycache__/` confirms execution under pytest 9.0.3 (`cpython-313-pytest-9.0.3.pyc`).
- **Import Patterns**:
  - Agents: `from agents.<agent_name> import <agent_name>`
  - Tools: `from tools import <tool_name>` or `from tools.<tool_name> import <tool_name>`
- **Test Utilities & Fixtures**: Tools use `setUp()` / `tearDown()` to create temporary test files and invoke tool functions via `<tool_module>.<tool_function>.invoke({...})`.

---

## 2. Logic Chain

1. **Premise 1 (Observation 1.1)**: `tool_maker.py` hardcodes `"Debian 11"`, `apt-packages-list.txt`, and `apt-get install` instructions in its system prompt.
2. **Premise 2 (Observation 1.2)**: When AgentK runs outside of its Docker container (e.g. natively on macOS Darwin, Ubuntu, Fedora, or Alpine), `apt-get` may be unavailable or inappropriate. On macOS, calling `apt-get` fails with command execution errors (`apt-get: command not found`).
3. **Premise 3**: Host environment details can be determined dynamically at runtime using standard Python modules (`platform`, `shutil.which`). Alternatively, OS context can be injected explicitly via arguments or environment variables.
4. **Deduction 1**: Hardcoding Debian 11 breaks Control Plane & Path Portability. Refactoring `tool_maker.py` to generate system prompts dynamically—incorporating host OS detection and configurable `os_context` overrides—will restore cross-platform functionality.
5. **Deduction 2 (Observation 1.3)**: Any refactored prompt generator and function signature in `tool_maker.py` must maintain backward compatibility with existing `unittest` / `pytest` suites and import patterns.

---

## 3. Detailed Refactoring Instructions

### 3.1 Helper Function for Platform & Package Manager Detection
Add a platform detection function to `utils.py` (or a dedicated `config/platform.py` module):

```python
import platform
import shutil
import os

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
```

### 3.2 Dynamic System Prompt Builder in `agents/tool_maker.py`
Replace the static `system_prompt = """..."""` module variable with a dynamic builder function:

```python
def get_os_guidance_prompt(os_context: str | dict | None = None) -> str:
    """Generate OS-specific dependency guidance for system prompt."""
    if isinstance(os_context, str):
        return os_context

    # Auto-detect platform if context not explicitly provided
    info = utils.get_platform_info()
    os_display = info["os_display"]
    pkg_mgr = info["pkg_manager"]
    pkg_file = info["pkg_list_file"]

    lines = [f"You are running on {os_display}."]

    if pkg_mgr and pkg_file:
        lines.append(f"You can check installed system packages in the `{pkg_file}` file.")
        if pkg_mgr == "apt-get":
            lines.append(f"If OS dependencies are missing you MUST install them by adding them to the end of `{pkg_file}` and using `xargs -a {pkg_file} apt-get install -y`.")
        elif pkg_mgr == "brew":
            lines.append(f"If OS dependencies are missing you MUST install them by adding them to `{pkg_file}` and using `brew install <package>`.")
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
The "K" stands kernel, meaning small core. The aim is for AgentK to be the minimum set of agents and tools necessary for it to bootstrap itself and then grow its own mind.

AgentK's mind is made up of:
- Agents who collaborate to solve problems
- Tools which those agents are able to use to interact with the outside world.

Your responses must be either an inner monologue or a message to the user.
If you are intending to call tools, then your response must be a succinct summary of your inner thoughts.
Else, your response is a message the user.  

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
When writing a tool, make sure to include a docstring on the function that succintly describes what the tool does.
Always include a test file that verifies the intended behaviour of the tool.
Use write_to_file tool to write the tool and test to disk.
Verify the tests pass by running the shell command `python -m unittest path_to_test_file`.
The test must pass before the tool is considered complete.
You can check installed python dependencies in the `requirements.txt` file.
If python dependencies are missing you MUST install them by adding them to the end of `requirements.txt` and using `pip install -r requirements.txt`.
{os_section}
If you need human input to finish a tool (eg. you need them to sign up for an account and provide an API key) use the request_human_input tool.

Example:
tools/add_smiley_face.py
```
from langchain_core.tools import tool

@tool
def add_smiley_face(text: str) -> str:
    \"\"\"Adds an asccii face to the end of the supplied text.\"\"\"
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
```

### 3.3 Refactoring `tool_maker` Entry Point
Update `tool_maker(...)` signature to accept an optional `os_context` parameter:

```python
def tool_maker(task: str, os_context: str | dict | None = None) -> str:
    """Creates new tools for agents to use."""
    prompt = build_tool_maker_prompt(os_context)
    return graph.invoke(
        {"messages": [SystemMessage(prompt), HumanMessage(task)]}
    )
```

---

## 4. Caveats

1. **Host Package Privileges**: Package managers on host systems (e.g. `brew`, `dnf`, `apt-get`) may require different flags or interactive permissions (e.g., `sudo` for `apt-get` vs non-root for `brew`).
2. **Container Compatibility**: The project container (`Dockerfile`) still uses Debian 11 and `apt-packages-list.txt`. Dynamic detection ensures container builds continue using `apt-get` while native host runs adapt to the host platform.
3. **Read-Only Scope**: This report is produced under read-only investigation rules. Implementation must be performed by an assigned implementer agent or developer.

---

## 5. Conclusion

1. Hardcoded Debian 11 specifications in `agents/tool_maker.py` (lines 44–46) break platform portability when running outside the default container environment.
2. Introducing `get_platform_info()` in `utils.py` and refactoring `tool_maker.py` to use a dynamic prompt generator (`build_tool_maker_prompt`) with configurable `os_context` makes AgentK fully OS-agnostic.
3. Test suite conventions rely on Python's `unittest` framework with standard imports (`from agents.<name> import <name>`, `from tools import <name>`) and main execution guards (`unittest.main()`).

---

## 6. Verification Method

To verify the analysis and proposed refactoring independently:

1. **Inspect `tool_maker.py`**:
   ```bash
   grep -n -C 3 "Debian" /Users/ricardo/AgentK/agents/tool_maker.py
   ```
   Confirm lines 44–46 contain hardcoded Debian 11 and `apt-get` strings.

2. **Run Test Suites**:
   ```bash
   python -m unittest discover -s tests
   # or using pytest
   pytest tests/
   ```
   Verify all current tests pass.

3. **Verify Dynamic Platform Detection**:
   Execute the following in a Python terminal on host platform (macOS/Linux):
   ```python
   import platform, shutil
   print("OS:", platform.system(), platform.release())
   print("Package Manager:", "apt-get" if shutil.which("apt-get") else ("brew" if shutil.which("brew") else "other"))
   ```
   Confirm detection returns accurate host platform details.
