import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from agents.agent_smith import (
    BASE_DIR,
    agent_smith,
    check_for_tool_calls,
    get_system_prompt,
    graph,
    load_agent_template,
)


class TestAgentSmith(unittest.TestCase):
    def test_callable_interface(self):
        """Verify that agent_smith function and graph are defined and callable."""
        self.assertTrue(callable(agent_smith))
        self.assertIsNotNone(graph)

    def test_load_agent_template(self):
        """Test loading template files using base_dir resolution."""
        agent_code, test_code = load_agent_template("web_researcher")
        self.assertIn("def web_researcher", agent_code)
        self.assertIn("TestWebResearcher", test_code)

    def test_get_system_prompt(self):
        """Test system prompt construction with template injection."""
        prompt = get_system_prompt("web_researcher")
        self.assertIn("You are agent_smith", prompt)
        self.assertIn("def web_researcher", prompt)
        self.assertIn("TestWebResearcher", prompt)

    def test_cwd_independence(self):
        """Verify template loading succeeds regardless of process CWD."""
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                os.chdir(tmp_dir)
                agent_code, test_code = load_agent_template("web_researcher")
                self.assertIn("def web_researcher", agent_code)
                prompt = get_system_prompt("web_researcher")
                self.assertIn("You are agent_smith", prompt)
            finally:
                os.chdir(original_cwd)

    def test_check_for_tool_calls_routing(self):
        """Test StateGraph routing logic for tool calls vs END."""
        mock_msg_with_tools = MagicMock()
        mock_msg_with_tools.tool_calls = [{"name": "write_to_file", "args": {}}]
        mock_msg_with_tools.content = "I will write a file"

        result_tools = check_for_tool_calls({"messages": [mock_msg_with_tools]})
        self.assertEqual(result_tools, "tools")

        mock_msg_no_tools = MagicMock()
        mock_msg_no_tools.tool_calls = []
        mock_msg_no_tools.content = "Done"

        result_end = check_for_tool_calls({"messages": [mock_msg_no_tools]})
        self.assertEqual(result_end, "__end__")


if __name__ == "__main__":
    unittest.main()
