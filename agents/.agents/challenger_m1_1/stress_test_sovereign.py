#!/usr/bin/env python3
"""
Empirical Stress Test Harness for sovereign_gate.py
====================================================
Tests path portability, symlink traversal, relative path traversal,
shell regex blocking, and allow-listing for non-destructive operations.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Project root for AgentK repository
PROJECT_ROOT = Path(__file__).resolve().parents[3] # /Users/ricardo/AgentK
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Mock or import google.antigravity modules
try:
    from google.antigravity import types
    def make_tool_call(name: str, args: dict, canonical_path: str = None):
        return types.ToolCall(name=name, args=args, canonical_path=canonical_path)
except ImportError:
    class DummyToolCall:
        def __init__(self, name: str, args: dict, canonical_path: str = None):
            self.name = name
            self.args = args
            self.canonical_path = canonical_path
            
    def make_tool_call(name: str, args: dict, canonical_path: str = None):
        return DummyToolCall(name, args, canonical_path)

import agents.sovereign_gate as sovereign_gate

pass_count = 0
fail_count = 0
results_log = []

def record_result(test_name: str, passed: bool, details: str):
    global pass_count, fail_count
    if passed:
        pass_count += 1
        status = "PASS"
    else:
        fail_count += 1
        status = "FAIL"
    results_log.append({"name": test_name, "status": status, "details": details})
    print(f"[{status}] {test_name}: {details}")


def test_dynamic_project_root_resolution():
    print("\n--- Test Suite 1: Dynamic PROJECT_ROOT Resolution ---")
    orig_cwd = os.getcwd()
    try:
        # Test CWD /tmp
        os.chdir("/tmp")
        expected_root = PROJECT_ROOT.resolve()
        actual_root = sovereign_gate.PROJECT_ROOT.resolve()
        passed = (actual_root == expected_root)
        record_result(
            "PROJECT_ROOT resolution from /tmp",
            passed,
            f"Expected {expected_root}, got {actual_root}"
        )

        # Test CWD /var/tmp
        if os.path.exists("/var/tmp"):
            os.chdir("/var/tmp")
            actual_root_var = sovereign_gate.PROJECT_ROOT.resolve()
            record_result(
                "PROJECT_ROOT resolution from /var/tmp",
                actual_root_var == expected_root,
                f"Expected {expected_root}, got {actual_root_var}"
            )
    finally:
        os.chdir(orig_cwd)


def test_agentk_root_env_override():
    print("\n--- Test Suite 2: AGENTK_ROOT Environment Variable Overrides ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        override_dir = Path(tmpdir).resolve()
        os.environ["AGENTK_ROOT"] = str(override_dir)
        try:
            protected = sovereign_gate.get_protected_paths()
            expected_protected = {str((override_dir / rel).resolve()) for rel in sovereign_gate.RELATIVE_PROTECTED_PATHS}
            passed = (protected == expected_protected)
            record_result(
                "AGENTK_ROOT override get_protected_paths",
                passed,
                f"Expected override paths under {override_dir}"
            )

            test_target = str(override_dir / "agent_kernel.py")
            is_prot = sovereign_gate.is_protected_path(test_target)
            record_result(
                "AGENTK_ROOT override is_protected_path",
                is_prot,
                f"Target {test_target} is_protected_path returned {is_prot}"
            )
        finally:
            if "AGENTK_ROOT" in os.environ:
                del os.environ["AGENTK_ROOT"]


def test_symlink_traversal():
    print("\n--- Test Suite 3: Symlink Traversal Attacks ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        symlink_target = tmp_path / "symlink_agent_kernel.py"
        real_protected = PROJECT_ROOT / "agent_kernel.py"

        try:
            os.symlink(real_protected, symlink_target)
            # Check if is_protected_path recognizes symlink pointing to protected file
            is_prot = sovereign_gate.is_protected_path(str(symlink_target))
            record_result(
                "Symlink pointing to agent_kernel.py",
                is_prot,
                f"Symlink {symlink_target} -> {real_protected}. Protected: {is_prot}"
            )

            # Test write tool call against symlink
            tc = make_tool_call("write_to_file", {"TargetFile": str(symlink_target)})
            denied = sovereign_gate._deny_protected_writes(tc)
            record_result(
                "Deny write tool call on symlink to protected file",
                denied,
                f"_deny_protected_writes returned {denied}"
            )
        except Exception as e:
            record_result("Symlink test exception", False, str(e))


def test_relative_path_traversal():
    print("\n--- Test Suite 4: Relative Path Traversal Attacks ---")
    # Test agents/../agent_kernel.py relative to repo root
    rel_path1 = os.path.join(str(PROJECT_ROOT), "agents", "..", "agent_kernel.py")
    is_prot1 = sovereign_gate.is_protected_path(rel_path1)
    record_result(
        "Path traversal: agents/../agent_kernel.py",
        is_prot1,
        f"is_protected_path('{rel_path1}') returned {is_prot1}"
    )

    # Test relative path string from inside agents/ directory
    orig_cwd = os.getcwd()
    try:
        os.chdir(str(PROJECT_ROOT / "agents"))
        rel_path2 = "../agent_kernel.py"
        is_prot2 = sovereign_gate.is_protected_path(rel_path2)
        record_result(
            "Path traversal: ../agent_kernel.py from agents/ dir",
            is_prot2,
            f"is_protected_path('{rel_path2}') from agents/ returned {is_prot2}"
        )
    finally:
        os.chdir(orig_cwd)


def test_shell_command_regex_blocking():
    print("\n--- Test Suite 5: Shell Command Regex Blocking ---")
    dangerous_commands = [
        "rm -rf agent_kernel.py",
        "echo 'hacked' > sovereign_gate.py",
        "cp payload.py agents/sdk_bridge.py",
        "chmod 777 self_heal.sh",
        "sed -i 's/foo/bar/g' requirements.txt",
        "tee -a tools/assign_agent_to_task.py < payload.py",
        f"rm -rf {str(PROJECT_ROOT / 'agents')}",
        "mv dangerous.py .git/hooks/pre-commit",
    ]

    for cmd in dangerous_commands:
        tc = make_tool_call("run_command", {"CommandLine": cmd})
        is_denied = sovereign_gate._deny_dangerous_commands(tc)
        record_result(
            f"Block dangerous command: '{cmd}'",
            is_denied,
            f"_deny_dangerous_commands returned {is_denied}"
        )


def test_allow_list_verification():
    print("\n--- Test Suite 6: Allow-list Verification for Non-destructive Read Operations ---")
    safe_commands = [
        "cat agent_kernel.py",
        "git status",
        "pytest",
        "ls -la agents/",
        "grep -r 'PROJECT_ROOT' .",
        "python3 -m unittest discover",
    ]

    for cmd in safe_commands:
        tc = make_tool_call("run_command", {"CommandLine": cmd})
        is_denied = sovereign_gate._deny_dangerous_commands(tc)
        record_result(
            f"Allow safe command: '{cmd}'",
            not is_denied,
            f"_deny_dangerous_commands returned {is_denied} (expected False)"
        )


if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING SOVEREIGN GATE EMPIRICAL STRESS TEST SUITE")
    print("=" * 70)
    
    test_dynamic_project_root_resolution()
    test_agentk_root_env_override()
    test_symlink_traversal()
    test_relative_path_traversal()
    test_shell_command_regex_blocking()
    test_allow_list_verification()

    print("\n" + "=" * 70)
    print(f"STRESS TEST SUMMARY: {pass_count} PASSED, {fail_count} FAILED")
    print("=" * 70)

    if fail_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)
