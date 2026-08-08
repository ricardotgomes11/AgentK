import os
import sys
from pathlib import Path

# Add project root to sys.path and remove tests dir to avoid namespace shadowing
PROJECT_ROOT = Path(__file__).resolve().parent.parent
script_dir = str(Path(__file__).resolve().parent)
if script_dir in sys.path:
    sys.path.remove(script_dir)
if "" in sys.path:
    sys.path.remove("")
if "." in sys.path:
    sys.path.remove(".")
sys.path.insert(0, str(PROJECT_ROOT))

# Ensure mock key for OPENAI if needed
os.environ.setdefault("OPENAI_API_KEY", "mock_key")

import unittest
from unittest.mock import patch, MagicMock

import utils
import agents.agent_smith as agent_smith
import agents.tool_maker as tool_maker


class TestCWDContextManager:
    """Context manager to temporarily change working directory."""
    def __init__(self, target_dir):
        self.target_dir = target_dir
        self.original_cwd = os.getcwd()

    def __enter__(self):
        os.chdir(self.target_dir)
        return self.target_dir

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.original_cwd)


class TestAgentSmithPathPortability(unittest.TestCase):
    """Test agent_smith.py template loading and prompt construction from arbitrary CWDs."""

    def test_load_agent_template_from_tmp(self):
        with TestCWDContextManager("/tmp"):
            agent_code, test_code = agent_smith.load_agent_template("web_researcher")
            self.assertIn("web_researcher", agent_code)
            self.assertIn("def test_", test_code)

    def test_load_agent_template_from_root(self):
        with TestCWDContextManager("/"):
            agent_code, test_code = agent_smith.load_agent_template("web_researcher")
            self.assertIn("web_researcher", agent_code)
            self.assertIn("def test_", test_code)

    def test_load_agent_template_custom_base_dir(self):
        with TestCWDContextManager("/tmp"):
            agent_code, test_code = agent_smith.load_agent_template("web_researcher", base_dir=PROJECT_ROOT)
            self.assertTrue(len(agent_code) > 0)
            self.assertTrue(len(test_code) > 0)

    def test_load_agent_template_nonexistent(self):
        with TestCWDContextManager("/tmp"):
            with self.assertRaises(FileNotFoundError):
                agent_smith.load_agent_template("non_existent_agent_xyz_123")

    def test_get_system_prompt_from_tmp(self):
        with TestCWDContextManager("/tmp"):
            prompt = agent_smith.get_system_prompt("web_researcher")
            self.assertIn("You are agent_smith", prompt)
            self.assertIn("web_researcher", prompt)
            self.assertIn("agents/web_researcher.py", prompt)

    def test_get_system_prompt_from_root(self):
        with TestCWDContextManager("/"):
            prompt = agent_smith.get_system_prompt("web_researcher")
            self.assertIn("You are agent_smith", prompt)
            self.assertIn("web_researcher", prompt)

    def test_get_system_prompt_custom_base_dir(self):
        with TestCWDContextManager("/tmp"):
            prompt = agent_smith.get_system_prompt("web_researcher", base_dir=PROJECT_ROOT)
            self.assertIn("You are agent_smith", prompt)


class TestUtilsPathResolutionFromTmp(unittest.TestCase):
    """Test utils.py path resolution and module loading when executed from /tmp."""

    def test_list_tools_from_tmp(self):
        with TestCWDContextManager("/tmp"):
            tools = utils.list_tools()
            self.assertIsInstance(tools, list)
            self.assertIn("read_file", tools)
            self.assertIn("overwrite_file", tools)
            self.assertIn("delete_file", tools)

    def test_list_agents_from_tmp(self):
        with TestCWDContextManager("/tmp"):
            agent_list = utils.list_agents()
            self.assertIsInstance(agent_list, list)
            self.assertIn("agent_smith", agent_list)
            self.assertIn("tool_maker", agent_list)
            self.assertNotIn("__init__", agent_list)

    def test_all_tool_functions_from_tmp(self):
        with TestCWDContextManager("/tmp"):
            tool_funcs = utils.all_tool_functions()
            self.assertIsInstance(tool_funcs, list)
            self.assertGreater(len(tool_funcs), 0)
            func_names = [f.name if hasattr(f, 'name') else f.__name__ for f in tool_funcs]
            self.assertIn("read_file", func_names)

    def test_all_agents_from_tmp(self):
        with TestCWDContextManager("/tmp"):
            agents_dict = utils.all_agents()
            self.assertIsInstance(agents_dict, dict)
            self.assertIn("agent_smith", agents_dict)
            self.assertIn("tool_maker", agents_dict)
            self.assertNotIn("hermes", agents_dict)

    def test_list_broken_tools_from_tmp(self):
        with TestCWDContextManager("/tmp"):
            broken_tools = utils.list_broken_tools()
            self.assertEqual(broken_tools, {})

    def test_list_broken_agents_from_tmp(self):
        with TestCWDContextManager("/tmp"):
            broken_agents = utils.list_broken_agents()
            # Note: sovereign_gate and sdk_bridge do not define agent functions matching their module name
            self.assertIn("sovereign_gate", broken_agents)
            self.assertIn("sdk_bridge", broken_agents)


class TestOSContextAndToolMakerPrompt(unittest.TestCase):
    """Test platform info detection and tool_maker system prompt generation across OS contexts."""

    def test_get_platform_info_host(self):
        info = utils.get_platform_info()
        self.assertIn("system", info)
        self.assertIn("os_display", info)
        self.assertIn("pkg_manager", info)
        self.assertIn("pkg_list_file", info)

    @patch("platform.system", return_value="Darwin")
    @patch("platform.mac_ver", return_value=("14.5", ("", "", ""), "arm64"))
    @patch("shutil.which")
    def test_get_platform_info_darwin(self, mock_which, mock_mac_ver, mock_system):
        mock_which.side_effect = lambda cmd: "/usr/local/bin/brew" if cmd == "brew" else None
        info = utils.get_platform_info()
        self.assertEqual(info["system"], "Darwin")
        self.assertEqual(info["os_display"], "macOS 14.5")
        self.assertEqual(info["pkg_manager"], "brew")
        self.assertEqual(info["pkg_list_file"], "brew-packages-list.txt")

    @patch("platform.system", return_value="Linux")
    @patch("platform.release", return_value="5.15.0-generic")
    @patch("shutil.which")
    def test_get_platform_info_linux_apt(self, mock_which, mock_release, mock_system):
        mock_which.side_effect = lambda cmd: "/usr/bin/apt-get" if cmd == "apt-get" else None
        info = utils.get_platform_info()
        self.assertEqual(info["system"], "Linux")
        self.assertEqual(info["os_display"], "Linux (5.15.0-generic)")
        self.assertEqual(info["pkg_manager"], "apt-get")
        self.assertEqual(info["pkg_list_file"], "apt-packages-list.txt")

    @patch("platform.system", return_value="Linux")
    @patch("platform.release", return_value="6.1.0")
    @patch("shutil.which")
    def test_get_platform_info_linux_dnf(self, mock_which, mock_release, mock_system):
        mock_which.side_effect = lambda cmd: "/usr/bin/dnf" if cmd == "dnf" else None
        info = utils.get_platform_info()
        self.assertEqual(info["pkg_manager"], "dnf")
        self.assertEqual(info["pkg_list_file"], "dnf-packages-list.txt")

    @patch("platform.system", return_value="Windows")
    @patch("platform.release", return_value="11")
    def test_get_platform_info_windows(self, mock_release, mock_system):
        info = utils.get_platform_info()
        self.assertEqual(info["system"], "Windows")
        self.assertEqual(info["os_display"], "Windows 11")
        self.assertIsNone(info["pkg_manager"])
        self.assertIsNone(info["pkg_list_file"])

    @patch("platform.system", return_value="FreeBSD")
    @patch("platform.release", return_value="13.0-RELEASE")
    def test_get_platform_info_unknown_os(self, mock_release, mock_system):
        info = utils.get_platform_info()
        self.assertEqual(info["system"], "FreeBSD")
        self.assertEqual(info["os_display"], "FreeBSD 13.0-RELEASE")
        self.assertIsNone(info["pkg_manager"])
        self.assertIsNone(info["pkg_list_file"])

    def test_get_os_guidance_prompt_string(self):
        prompt = tool_maker.get_os_guidance_prompt("Custom OS instructions")
        self.assertEqual(prompt, "Custom OS instructions")

    def test_get_os_guidance_prompt_dict_darwin(self):
        context = {
            "os_display": "macOS 14.0",
            "pkg_manager": "brew",
            "pkg_list_file": "brew-packages-list.txt",
        }
        prompt = tool_maker.get_os_guidance_prompt(context)
        self.assertIn("You are running on macOS 14.0.", prompt)
        self.assertIn("brew-packages-list.txt", prompt)
        self.assertIn("brew install <package>", prompt)

    def test_get_os_guidance_prompt_dict_linux_apt(self):
        context = {
            "os_display": "Linux (5.15.0)",
            "pkg_manager": "apt-get",
            "pkg_list_file": "apt-packages-list.txt",
        }
        prompt = tool_maker.get_os_guidance_prompt(context)
        self.assertIn("You are running on Linux (5.15.0).", prompt)
        self.assertIn("apt-packages-list.txt", prompt)
        self.assertIn("apt-get install -y", prompt)

    def test_get_os_guidance_prompt_dict_linux_other_pkg_mgr(self):
        context = {
            "os_display": "Fedora Linux",
            "pkg_manager": "dnf",
            "pkg_list_file": "dnf-packages-list.txt",
        }
        prompt = tool_maker.get_os_guidance_prompt(context)
        self.assertIn("You are running on Fedora Linux.", prompt)
        self.assertIn("dnf-packages-list.txt", prompt)
        self.assertIn("install them using `dnf`", prompt)

    def test_get_os_guidance_prompt_dict_no_pkg_mgr(self):
        context = {
            "os_display": "Windows 11",
            "pkg_manager": None,
            "pkg_list_file": None,
        }
        prompt = tool_maker.get_os_guidance_prompt(context)
        self.assertIn("You are running on Windows 11.", prompt)
        self.assertIn("use host system tools or use the request_human_input tool", prompt)

    def test_get_os_guidance_prompt_none(self):
        prompt = tool_maker.get_os_guidance_prompt(None)
        self.assertIn("You are running on", prompt)

    def test_build_tool_maker_prompt_various_contexts(self):
        prompt_darwin = tool_maker.build_tool_maker_prompt({"os_display": "macOS", "pkg_manager": "brew", "pkg_list_file": "brew-packages-list.txt"})
        self.assertIn("You are tool_maker", prompt_darwin)
        self.assertIn("macOS", prompt_darwin)

        prompt_str = tool_maker.build_tool_maker_prompt("Custom OS Prompt")
        self.assertIn("Custom OS Prompt", prompt_str)

        prompt_none = tool_maker.build_tool_maker_prompt(None)
        self.assertIn("You are tool_maker", prompt_none)


if __name__ == "__main__":
    unittest.main()
