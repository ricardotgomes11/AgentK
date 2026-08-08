"""
Unit Tests for Tool Maker Prompt Generation and Platform Info
File: tests/agents/test_tool_maker.py
"""

import unittest
from unittest.mock import patch
import utils
from agents.tool_maker import (
    get_os_guidance_prompt,
    build_tool_maker_prompt,
    tool_maker,
)


class TestToolMaker(unittest.TestCase):
    def test_get_platform_info(self):
        info = utils.get_platform_info()
        self.assertIn("system", info)
        self.assertIn("os_display", info)
        self.assertIn("pkg_manager", info)
        self.assertIn("pkg_list_file", info)

    def test_get_os_guidance_prompt_string_override(self):
        prompt = get_os_guidance_prompt("Custom OS Guidance")
        self.assertEqual(prompt, "Custom OS Guidance")

    def test_get_os_guidance_prompt_dict(self):
        os_ctx = {
            "os_display": "Ubuntu 22.04",
            "pkg_manager": "apt-get",
            "pkg_list_file": "apt-packages-list.txt",
        }
        prompt = get_os_guidance_prompt(os_ctx)
        self.assertIn("Ubuntu 22.04", prompt)
        self.assertIn("apt-packages-list.txt", prompt)
        self.assertIn("apt-get install -y", prompt)

    def test_get_os_guidance_prompt_brew(self):
        os_ctx = {
            "os_display": "macOS 14.0",
            "pkg_manager": "brew",
            "pkg_list_file": "brew-packages-list.txt",
        }
        prompt = get_os_guidance_prompt(os_ctx)
        self.assertIn("macOS 14.0", prompt)
        self.assertIn("brew install", prompt)

    def test_build_tool_maker_prompt(self):
        prompt = build_tool_maker_prompt()
        self.assertIn("You are tool_maker", prompt)
        self.assertIn("Tools MUST go in the `tools` directory.", prompt)

    def test_tool_maker_callable(self):
        self.assertTrue(callable(tool_maker))


if __name__ == "__main__":
    unittest.main()
