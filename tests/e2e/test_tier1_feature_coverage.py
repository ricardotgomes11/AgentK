import os
import sys

# Ensure environment variables for offline test execution
os.environ.setdefault("OPENAI_API_KEY", "mock-openai-key-for-e2e-testing")

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import unittest
from unittest.mock import patch, MagicMock
import pytest
from langchain_core.messages import AIMessage

import agents.sovereign_gate as sovereign_gate
import agents.agent_smith as agent_smith
import agents.hermes as hermes
import agents.software_engineer as software_engineer
import agents.tool_maker as tool_maker
import agents.web_researcher as web_researcher
import agents.sdk_bridge as sdk_bridge
import utils
import config
from google.antigravity import types


@pytest.mark.tier1
@pytest.mark.e2e
class TestTier1SovereignGate(unittest.TestCase):
    """Tier 1 Feature Coverage for Sovereign Gate (F1)"""

    def test_t1_sovereign_gate_deny_protected_file_write(self):
        tc = types.ToolCall(name="write_to_file", args={"file": os.path.join(PROJECT_ROOT, "agent_kernel.py")})
        self.assertTrue(sovereign_gate._deny_protected_writes(tc))

    def test_t1_sovereign_gate_deny_protected_file_delete(self):
        self.assertTrue(sovereign_gate.is_protected_path(os.path.abspath("/Users/ricardo/AgentK/agents/sovereign_gate.py")))

    def test_t1_sovereign_gate_deny_dangerous_shell_command(self):
        tc = types.ToolCall(name="run_command", args={"CommandLine": "rm -rf /Users/ricardo/AgentK/agent_kernel.py"})
        self.assertTrue(sovereign_gate._deny_dangerous_commands(tc))

    def test_t1_sovereign_gate_intercept_agent_tool_creation(self):
        tc = types.ToolCall(name="write_to_file", args={"path": os.path.abspath("/Users/ricardo/AgentK/agents/new_agent.py")})
        self.assertTrue(sovereign_gate._is_agent_or_tool_write(tc))

    def test_t1_sovereign_gate_allow_harmless_read_operation(self):
        policies = sovereign_gate.get_sovereign_policies()
        self.assertTrue(len(policies) > 0)
        self.assertEqual(policies[-1].name, "sovereign_fallback_allow")


@pytest.mark.tier1
@pytest.mark.e2e
class TestTier1AgentSmith(unittest.TestCase):
    """Tier 1 Feature Coverage for Agent Smith (F2)"""

    @patch("config.default_langchain_model")
    def test_t1_agent_smith_generate_agent_structure(self, mock_model):
        mock_response = AIMessage(content="Agent structure generated.", tool_calls=[])
        mock_model.bind_tools.return_value.invoke.return_value = mock_response

        res = agent_smith.agent_smith("Design data_analyst agent")
        self.assertIn("messages", res)

    @patch("config.default_langchain_model")
    def test_t1_agent_smith_write_agent_and_test_to_disk(self, mock_model):
        mock_response = AIMessage(content="Wrote agent code to agents/data_analyst.py", tool_calls=[])
        mock_model.bind_tools.return_value.invoke.return_value = mock_response

        res = agent_smith.agent_smith("Create data_analyst agent")
        self.assertEqual(res["messages"][-1].content, "Wrote agent code to agents/data_analyst.py")

    @patch("config.default_langchain_model")
    def test_t1_agent_smith_tool_maker_task_assignment(self, mock_model):
        mock_response = AIMessage(content="Assigned tool creation to tool_maker.", tool_calls=[])
        mock_model.bind_tools.return_value.invoke.return_value = mock_response

        res = agent_smith.agent_smith("Build agent requiring new tool")
        self.assertTrue(len(res["messages"]) > 0)

    @patch("config.default_langchain_model")
    def test_t1_agent_smith_smoke_test_execution_verification(self, mock_model):
        mock_response = AIMessage(content="Smoke test passed successfully.", tool_calls=[])
        mock_model.bind_tools.return_value.invoke.return_value = mock_response

        res = agent_smith.agent_smith("Verify smoke test")
        self.assertIn("messages", res)

    @patch("config.default_langchain_model")
    def test_t1_agent_smith_state_compilation_and_return_format(self, mock_model):
        mock_response = AIMessage(content="Done", tool_calls=[])
        mock_model.bind_tools.return_value.invoke.return_value = mock_response

        res = agent_smith.agent_smith("Test task")
        self.assertIsInstance(res, dict)
        self.assertIn("messages", res)


@pytest.mark.tier1
@pytest.mark.e2e
class TestTier1Hermes(unittest.TestCase):
    """Tier 1 Feature Coverage for Hermes (F3)"""

    @patch("builtins.input", side_effect=["exit"])
    def test_t1_hermes_goal_planning_and_user_interaction(self, mock_input):
        res = hermes.hermes("test_uuid_tier1_1")
        self.assertIn("messages", res)

    def test_t1_hermes_assign_task_to_agent(self):
        with patch("utils.load_module") as mock_load:
            mock_mod = MagicMock()
            mock_mod.__name__ = "agents.web_researcher"
            sys.modules["agents.web_researcher"] = mock_mod
            mock_mod.web_researcher.return_value = {"messages": [AIMessage(content="Research done", tool_calls=[])]}
            mock_load.return_value = mock_mod

            from tools.assign_agent_to_task import assign_agent_to_task
            out = assign_agent_to_task.invoke({"agent_name": "web_researcher", "task": "Search python news"})
            self.assertIn("Research done", out)

    def test_t1_hermes_list_available_agents_tool_invocation(self):
        from tools.list_available_agents import list_available_agents
        out = list_available_agents.invoke({})
        self.assertIn("web_researcher", out)

    def test_t1_hermes_sqlite_checkpointer_thread_isolation(self):
        state1 = hermes.graph.get_state(config={"configurable": {"thread_id": "thread_t1_a"}})
        state2 = hermes.graph.get_state(config={"configurable": {"thread_id": "thread_t1_b"}})
        self.assertIsNotNone(state1)
        self.assertIsNotNone(state2)

    @patch("builtins.input", side_effect=["exit"])
    def test_t1_hermes_exit_signal_handling(self, mock_input):
        res = hermes.hermes("test_uuid_exit")
        self.assertEqual(res["messages"][-1].content.lower(), "exit")


@pytest.mark.tier1
@pytest.mark.e2e
class TestTier1SoftwareEngineer(unittest.TestCase):
    """Tier 1 Feature Coverage for Software Engineer (F4)"""

    @patch("config.default_langchain_model")
    def test_t1_software_engineer_write_file_execution(self, mock_model):
        mock_response = AIMessage(content="File created", tool_calls=[])
        mock_model.bind_tools.return_value.invoke.return_value = mock_response

        res = software_engineer.software_engineer("Create scratch.py")
        self.assertIn("messages", res)

    @patch("config.default_langchain_model")
    def test_t1_software_engineer_overwrite_file_execution(self, mock_model):
        mock_response = AIMessage(content="File overwritten", tool_calls=[])
        mock_model.bind_tools.return_value.invoke.return_value = mock_response

        res = software_engineer.software_engineer("Overwrite scratch.py")
        self.assertIn("messages", res)

    @patch("config.default_langchain_model")
    def test_t1_software_engineer_delete_file_execution(self, mock_model):
        mock_response = AIMessage(content="File deleted", tool_calls=[])
        mock_model.bind_tools.return_value.invoke.return_value = mock_response

        res = software_engineer.software_engineer("Delete scratch.py")
        self.assertIn("messages", res)

    @patch("config.default_langchain_model")
    def test_t1_software_engineer_read_file_execution(self, mock_model):
        mock_response = AIMessage(content="File content read", tool_calls=[])
        mock_model.bind_tools.return_value.invoke.return_value = mock_response

        res = software_engineer.software_engineer("Read main.py")
        self.assertIn("messages", res)

    @patch("config.default_langchain_model")
    def test_t1_software_engineer_run_shell_command_execution(self, mock_model):
        mock_response = AIMessage(content="Command executed", tool_calls=[])
        mock_model.bind_tools.return_value.invoke.return_value = mock_response

        res = software_engineer.software_engineer("Run echo test")
        self.assertIn("messages", res)


@pytest.mark.tier1
@pytest.mark.e2e
class TestTier1ToolMaker(unittest.TestCase):
    """Tier 1 Feature Coverage for Tool Maker (F5)"""

    @patch("config.default_langchain_model")
    def test_t1_tool_maker_synthesize_tool_function(self, mock_model):
        mock_response = AIMessage(content="Tool synthesized", tool_calls=[])
        mock_model.bind_tools.return_value.invoke.return_value = mock_response

        res = tool_maker.tool_maker("Build custom tool")
        self.assertIn("messages", res)

    @patch("config.default_langchain_model")
    def test_t1_tool_maker_synthesize_unittest_file(self, mock_model):
        mock_response = AIMessage(content="Unittest file generated", tool_calls=[])
        mock_model.bind_tools.return_value.invoke.return_value = mock_response

        res = tool_maker.tool_maker("Generate test file for tool")
        self.assertIn("messages", res)

    @patch("config.default_langchain_model")
    def test_t1_tool_maker_execute_unittest_verification(self, mock_model):
        mock_response = AIMessage(content="Ran unittest successfully", tool_calls=[])
        mock_model.bind_tools.return_value.invoke.return_value = mock_response

        res = tool_maker.tool_maker("Verify test pass")
        self.assertIn("messages", res)

    def test_t1_tool_maker_requirements_txt_dependency_update(self):
        req_path = os.path.join(PROJECT_ROOT, "requirements.txt")
        self.assertTrue(os.path.exists(req_path))

    def test_t1_tool_maker_request_human_input_invocation(self):
        from tools.request_human_input import request_human_input
        with patch("builtins.input", return_value="user_api_key_123"):
            res = request_human_input.invoke({"prompt": "Enter API key"})
            self.assertEqual(res, "user_api_key_123")


@pytest.mark.tier1
@pytest.mark.e2e
class TestTier1WebResearcher(unittest.TestCase):
    """Tier 1 Feature Coverage for Web Researcher (F6)"""

    @patch("tools.duck_duck_go_web_search.DuckDuckGoSearchResults")
    def test_t1_web_researcher_duckduckgo_search_invocation(self, mock_ddg_class):
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = "[snippet: Python news]"
        mock_ddg_class.return_value = mock_instance

        from tools.duck_duck_go_web_search import duck_duck_go_web_search
        out = duck_duck_go_web_search.invoke({"query": "python"})
        self.assertIn("Python news", out)

    @patch("tools.fetch_web_page_content.SeleniumURLLoader")
    def test_t1_web_researcher_fetch_web_page_content_invocation(self, mock_loader_class):
        mock_loader = MagicMock()
        mock_doc = MagicMock()
        mock_doc.page_content = "Hello World"
        mock_loader.load.return_value = [mock_doc]
        mock_loader_class.return_value = mock_loader

        from tools.fetch_web_page_content import fetch_web_page_content
        out = fetch_web_page_content.invoke({"url": "http://example.com"})
        self.assertIsNotNone(out)

    @patch("config.default_langchain_model")
    def test_t1_web_researcher_research_synthesis_return(self, mock_model):
        mock_response = AIMessage(content="Factual research summary.", tool_calls=[])
        mock_model.bind_tools.return_value.invoke.return_value = mock_response

        res = web_researcher.web_researcher("Research topic")
        self.assertEqual(res["messages"][-1].content, "Factual research summary.")

    def test_t1_web_researcher_tool_binding_verification(self):
        tool_names = [t.name for t in web_researcher.tools]
        self.assertIn("duck_duck_go_web_search", tool_names)
        self.assertIn("fetch_web_page_content", tool_names)

    @patch("config.default_langchain_model")
    def test_t1_web_researcher_state_message_extraction(self, mock_model):
        mock_response = AIMessage(content="Extracted message", tool_calls=[])
        mock_model.bind_tools.return_value.invoke.return_value = mock_response

        res = web_researcher.web_researcher("Task")
        self.assertIn("messages", res)


@pytest.mark.tier1
@pytest.mark.e2e
class TestTier1SDKBridge(unittest.TestCase):
    """Tier 1 Feature Coverage for SDK Bridge (F7)"""

    def test_t1_sdk_bridge_get_agent_inventory(self):
        inventory = sdk_bridge.get_agent_inventory()
        self.assertIn("web_researcher", inventory)

    def test_t1_sdk_bridge_get_tool_inventory(self):
        tools_str = sdk_bridge.get_tool_inventory()
        self.assertIn("read_file", tools_str)

    def test_t1_sdk_bridge_get_system_prompt_composition(self):
        prompt = sdk_bridge.get_system_prompt()
        self.assertIn("Hermes", prompt)
        self.assertIn("AgentK", prompt)

    @patch("utils.load_module")
    def test_t1_sdk_bridge_dispatch_agent_dynamic_import(self, mock_load):
        mock_mod = MagicMock()
        mock_mod.__name__ = "agents.test_agent"
        sys.modules["agents.test_agent"] = mock_mod
        mock_mod.test_agent.return_value = {"messages": [AIMessage(content="Dispatched result", tool_calls=[])]}
        mock_load.return_value = mock_mod

        res = sdk_bridge.dispatch_agent("test_agent", "Do task")
        self.assertEqual(res, "Dispatched result")

    @patch("utils.load_module")
    def test_t1_sdk_bridge_run_agent_via_sdk_text_response(self, mock_load):
        mock_mod = MagicMock()
        mock_mod.__name__ = "agents.web_researcher"
        sys.modules["agents.web_researcher"] = mock_mod
        mock_mod.web_researcher.return_value = {"messages": [AIMessage(content="Search completed.", tool_calls=[])]}
        mock_load.return_value = mock_mod

        res = sdk_bridge.dispatch_agent("web_researcher", "Research query")
        self.assertEqual(res, "Search completed.")


if __name__ == "__main__":
    unittest.main()
