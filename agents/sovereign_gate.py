"""
AgentK Sovereign Gate
=====================
Defines access policies and user confirmation flows to secure AgentK's
control plane from rogue self-evolution attempts.
Seals the 13 breaches identified in the stress test.
"""

import os
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace
try:
    from google.antigravity.hooks import policy
    from google.antigravity import types
except ImportError:
    class _PolicyStub:
        Policy = object
        @staticmethod
        def deny(tool, when=None, name=None):
            return SimpleNamespace(name=name, tool=tool, when=when, action="deny")
        @staticmethod
        def ask_user(tool, handler=None, when=None, name=None):
            return SimpleNamespace(name=name, tool=tool, when=when, handler=handler, action="ask_user")
        @staticmethod
        def allow(tool, name=None):
            return SimpleNamespace(name=name, tool=tool, action="allow")

    class _TypesStub:
        class ToolCall:
            def __init__(self, name="", args=None, canonical_path=None):
                self.name = name
                self.args = args or {}
                self.canonical_path = canonical_path

    policy = _PolicyStub()
    types = _TypesStub()

# ---------------------------------------------------------------------------
# Dynamic Project Root Resolution
# ---------------------------------------------------------------------------
# Determine project root dynamically (parent of agents/ directory)
_ENV_ROOT = os.environ.get("AGENTK_ROOT")
PROJECT_ROOT = (Path(_ENV_ROOT).resolve() if _ENV_ROOT else Path(__file__).resolve().parents[1])

# Relative paths of protected control-plane files
RELATIVE_PROTECTED_PATHS = [
    "agent_kernel.py",
    "agents/sdk_bridge.py",
    "agents/sovereign_gate.py",
    "self_heal.sh",
    "requirements.txt",
    "tools/assign_agent_to_task.py",
]


def get_protected_paths() -> set[str]:
    """Returns absolute canonical path strings for all protected files."""
    env_root = os.environ.get("AGENTK_ROOT")
    root = Path(env_root).resolve() if env_root else PROJECT_ROOT
    return {str((root / rel_path).resolve()) for rel_path in RELATIVE_PROTECTED_PATHS}


PROTECTED_PATHS = get_protected_paths()


def is_protected_path(path: str | None) -> bool:
    """Returns True if path points to a protected control plane file or .git dir."""
    if not path:
        return False

    try:
        target_path = Path(path).resolve()
        target_str = str(target_path)
    except Exception:
        target_str = os.path.abspath(path)
        target_path = Path(target_str)

    # Check protected files set
    if target_str in get_protected_paths():
        return True

    # Protect git repository integrity (.git directory and all contents)
    env_root = os.environ.get("AGENTK_ROOT")
    root = Path(env_root).resolve() if env_root else PROJECT_ROOT
    git_dir = (root / ".git").resolve()
    try:
        if target_path == git_dir or git_dir in target_path.parents:
            return True
    except Exception:
        git_dir_str = str(git_dir)
        if target_str == git_dir_str or target_str.startswith(git_dir_str + os.sep):
            return True

    return False


def _is_agent_or_tool_write(tc: types.ToolCall) -> bool:
    """Returns True if the tool tries to create or edit an agent or tool script."""
    path = (
        tc.canonical_path
        or tc.args.get("path")
        or tc.args.get("TargetFile")
        or tc.args.get("source")
        or tc.args.get("dest")
        or tc.args.get("filename")
        or tc.args.get("filepath")
        or tc.args.get("file")
        or tc.args.get("file_path")
    )
    if not path:
        return False

    try:
        target_path = Path(path).resolve()
    except Exception:
        target_path = Path(os.path.abspath(path))

    env_root = os.environ.get("AGENTK_ROOT")
    root = Path(env_root).resolve() if env_root else PROJECT_ROOT
    agents_dir = (root / "agents").resolve()
    tools_dir = (root / "tools").resolve()

    return (
        target_path == agents_dir
        or agents_dir in target_path.parents
        or target_path == tools_dir
        or tools_dir in target_path.parents
    )


def _deny_protected_writes(tc: types.ToolCall) -> bool:
    """Returns True if the tool tries to modify protected files/directories."""
    # Look for paths in various arguments across tool variants
    for arg_name in ("path", "TargetFile", "source", "dest", "filename", "filepath", "file", "file_path"):
        if arg_name in tc.args and is_protected_path(tc.args[arg_name]):
            return True
    if tc.canonical_path and is_protected_path(tc.canonical_path):
        return True
    return False


def _deny_dangerous_commands(tc: types.ToolCall) -> bool:
    """Returns True if shell command attempts to modify protected areas, execute code on protected files, or run system destruction."""
    cmd = tc.args.get("CommandLine", "") or tc.args.get("command", "")
    if not cmd:
        return False

    # Unconditional block on security bypass/override attempts
    override_patterns = [
        "OVERRIDE_SECURITY",
        "DISABLE_SOVEREIGN",
        "IGNORE_GATE",
        "BYPASS_SECURITY",
        "DISABLE_SECURITY",
    ]
    if any(pattern in cmd for pattern in override_patterns):
        return True

    # Unconditional block on system-wide destructive commands
    destructive_system_patterns = [
        r"rm\s+-rf\s+/",
        r"rm\s+-rf\s+\*",
        r"rm\s+-rf\s+~",
        r"rm\s+-rf\s+\.",
        r"mkfs",
        r"dd\s+if=",
        r"chmod\s+-R\s+777",
    ]
    if any(re.search(pat, cmd) for pat in destructive_system_patterns):
        return True

    # Blocked destructive/executing operators and commands targeting kernel files
    destructive_pattern = r"(?:>>|>|\brm\b|\bmv\b|\bchmod\b|\bsed\b|\btee\b|\bcp\b|\bunlink\b|\bdd\b|\btruncate\b|\bpython3?\b|\bcurl\b|\bwget\b|\btouch\b|\bawk\b)"

    dangerous_keywords = [
        "agent_kernel",
        "sdk_bridge",
        "sovereign_gate",
        "self_heal",
        "requirements.txt",
        "assign_agent_to_task",
        ".git",
        "crontab",
    ]

    has_keyword = any(kw in cmd for kw in dangerous_keywords)
    has_destructive_op = bool(re.search(destructive_pattern, cmd))

    if "crontab" in cmd:
        return True

    if has_keyword and has_destructive_op:
        return True

    # Also block destructive operations containing explicit PROJECT_ROOT path string
    env_root = os.environ.get("AGENTK_ROOT")
    root = Path(env_root).resolve() if env_root else PROJECT_ROOT
    proj_root_str = str(root)
    if proj_root_str in cmd and has_destructive_op:
        return True

    return False


def console_approval_handler(tc: types.ToolCall) -> bool:
    """Prompts the creator on their local terminal to confirm high-impact actions."""
    print(f"\n⚠️  [SOVEREIGN GATE] Agent requested high-impact tool: {tc.name}")
    print(f"   Arguments: {tc.args}")
    try:
        ans = input("   Approve tool execution? (y/N): ")
        return ans.strip().lower() == "y"
    except (KeyboardInterrupt, EOFError):
        print("\n   [SOVEREIGN GATE] Aborted. Action denied.")
        return False


def get_sovereign_policies() -> list:
    """Returns the list of sealed policy constraints."""
    file_write_tools = [
        "write_to_file",
        "replace_file_content",
        "multi_replace_file_content",
        "create_file",
        "edit_file",
        "overwrite_file",
        "delete_file",
    ]
    command_tools = [
        "run_command",
        "run_shell_command",
    ]
    subagent_tools = [
        "start_subagent",
        "invoke_subagent",
        "define_subagent",
        "browser_subagent",
        "assign_agent_to_task",
    ]

    policies = []

    # 1. Deny raw writes to any protected files
    for tool in file_write_tools:
        policies.append(
            policy.deny(
                tool,
                when=_deny_protected_writes,
                name=f"sovereign_file_protection_{tool}",
            )
        )

    # 2. Intercept and require approval for new agent/tool creation or modification
    for tool in file_write_tools:
        policies.append(
            policy.ask_user(
                tool,
                handler=console_approval_handler,
                when=_is_agent_or_tool_write,
                name=f"sovereign_agent_tool_creation_{tool}",
            )
        )

    # 3. Deny shell command writes to protected files
    for tool in command_tools:
        policies.append(
            policy.deny(
                tool,
                when=_deny_dangerous_commands,
                name=f"sovereign_shell_write_protection_{tool}",
            )
        )

    # 4. Require creator approval for general shell commands
    for tool in command_tools:
        policies.append(
            policy.ask_user(
                tool,
                handler=console_approval_handler,
                name=f"sovereign_shell_approval_{tool}",
            )
        )

    # 5. Require creator approval for starting subagents (bypasses fork bombs)
    for tool in subagent_tools:
        policies.append(
            policy.ask_user(
                tool,
                handler=console_approval_handler,
                name=f"sovereign_subagent_approval_{tool}",
            )
        )

    # 6. Fallback: Allow all other read-only and harmless operations
    policies.append(policy.allow("*", name="sovereign_fallback_allow"))

    return policies


def evaluate_or_dispatch(tc: types.ToolCall) -> SimpleNamespace:
    """Public policy evaluation and dispatch path for sovereign gate."""
    if _deny_protected_writes(tc) or _deny_dangerous_commands(tc):
        return SimpleNamespace(denied=True, allowed=False, action="denied")

    return SimpleNamespace(denied=False, allowed=True, action="allowed")
