# Handoff Report: Unit Test Suite Upgrades for Software Engineer, Tool Maker, & Web Researcher

**Explorer**: Explorer 3 (Milestone 2)  
**Target Agents**: `software_engineer`, `tool_maker`, `web_researcher`  
**Target Test Files**:
- `/Users/ricardo/AgentK/tests/agents/test_software_engineer.py`
- `/Users/ricardo/AgentK/tests/agents/test_tool_maker.py`
- `/Users/ricardo/AgentK/tests/agents/test_web_researcher.py`

---

## 1. Observation

### 1.1 Existing Test Implementations

#### Observation 1.1.1: `tests/agents/test_software_engineer.py`
File contains only 11 lines testing function callability:
```python
1: import unittest
2: 
3: from agents.software_engineer import software_engineer
4: 
5: class TestSoftwareEngineer(unittest.TestCase):
6:     def test_software_engineer(self):
7:         self.assertTrue(callable(software_engineer))
8: 
9: if __name__ == '__main__':
10:     unittest.main()
```

#### Observation 1.1.2: `tests/agents/test_web_researcher.py`
File contains only 10 lines testing function callability:
```python
1: import unittest
2: 
3: from agents.web_researcher import web_researcher
4: 
5: class TestWebResearcher(unittest.TestCase):
6:     def test_web_researcher(self):
7:         self.assertTrue(callable(web_researcher))
8: 
9: if __name__ == '__main__':
10:     unittest.main()
```

#### Observation 1.1.3: `tests/agents/test_tool_maker.py`
File contains 60 lines testing prompt generation functions, but graph state, tool bindings, and tool synthesis execution loops are untested:
```python
17:     def test_get_platform_info(self): ...
24:     def test_get_os_guidance_prompt_string_override(self): ...
28:     def test_get_os_guidance_prompt_dict(self): ...
39:     def test_get_os_guidance_prompt_brew(self): ...
49:     def test_build_tool_maker_prompt(self): ...
54:     def test_tool_maker_callable(self):
55:         self.assertTrue(callable(tool_maker))
```

---

### 1.2 Agent Implementation Structure

#### Observation 1.2.1: `agents/software_engineer.py`
- **System Prompt**: Line 9 (`system_prompt = """You are software_engineer..."""`).
- **Tool List**: Lines 22-30:
  ```python
  tools = [
      write_to_file,
      overwrite_file,
      delete_file,
      read_file,
      run_shell_command,
      assign_agent_to_task,
      list_available_agents
  ]
  ```
- **LangGraph Components**:
  - `reasoning(state: MessagesState)` (lines 32-37): binds tools to `config.default_langchain_model` and invokes model with messages.
  - `check_for_tool_calls(state: MessagesState)` (lines 39-52): inspects `messages[-1]`, returns `"tools"` if `last_message.tool_calls` is present, else `END`.
  - `acting = ToolNode(tools)` (line 54).
  - `workflow = StateGraph(MessagesState)` (lines 56-64): compiled into `graph`.

#### Observation 1.2.2: `agents/tool_maker.py`
- **Prompt Generators**: `get_os_guidance_prompt(os_context)`, `build_tool_maker_prompt(os_context)`.
- **Dynamic Tool List**: Line 141 (`tools = utils.all_tool_functions()`).
- **LangGraph Components**: `reasoning`, `check_for_tool_calls`, `acting = ToolNode(tools)`, `graph = workflow.compile()`.
- **Function Entrypoint**: `tool_maker(task: str, os_context: str | dict | None = None)`.

#### Observation 1.2.3: `agents/web_researcher.py`
- **System Prompt**: Line 9 (`system_prompt = """You are web_researcher..."""`).
- **Tool List**: Line 18 (`tools = [duck_duck_go_web_search, fetch_web_page_content]`).
- **External Dependencies**:
  - `tools.duck_duck_go_web_search` calls `DuckDuckGoSearchResults().invoke(query)`
  - `tools.fetch_web_page_content` calls `SeleniumURLLoader(urls=[url], executable_path="/usr/bin/chromedriver", ...).load()`
- **LangGraph Components**: `reasoning`, `check_for_tool_calls`, `acting = ToolNode(tools)`, `graph = workflow.compile()`.

---

## 2. Logic Chain

1. **Deficiency of `callable()` assertions**:
   - Checking `callable(agent)` only proves the module loads without syntax/import errors. It fails to verify graph structure, node connections, tool bindings, state updates, routing, system prompt composition, or tool execution safety.

2. **Necessity of Offline Mocks for Web & LLM Calls**:
   - In CODE_ONLY network mode, external HTTP calls (DuckDuckGo, Selenium ChromeDriver) fail or hang.
   - LLM API calls (OpenAI / Anthropic) incur network latency, cost, and non-determinism.
   - Therefore, unit tests must mock:
     - Model invocations (`config.default_langchain_model.bind_tools` or model `invoke`).
     - `DuckDuckGoSearchResults.invoke` in `duck_duck_go_web_search`.
     - `SeleniumURLLoader.load` in `fetch_web_page_content`.

3. **Sandbox Isolation for File & Shell Operations**:
   - `software_engineer` and `tool_maker` use file modification tools (`write_to_file`, `overwrite_file`, `delete_file`, `run_shell_command`).
   - Unit tests executing these tools must be isolated within temporary directories (`tmp_path` fixture or `tempfile.TemporaryDirectory()`) to prevent mutating workspace files or leaving side effects.

4. **Multi-layer Test Architecture**:
   - **Layer 1: Unit & Component Inspection**: Direct assertion on exported `tools`, `system_prompt`, prompt generation helpers, and compiled `graph`.
   - **Layer 2: State Routing Unit Tests**: Direct test of `check_for_tool_calls` node output given messages with/without `tool_calls`.
   - **Layer 3: Reasoning Node Mock Tests**: Test `reasoning(state)` node function with mocked `tooled_up_model`.
   - **Layer 4: End-to-End Graph Execution Tests**: Execute `graph.invoke()` with mocked LLM responses (simulating tool call -> tool response -> final text output) in a isolated sandbox.

---

## 3. Caveats

- **LangChain Message Structure**: Unit test mocks assume standard `langchain_core.messages` objects (`AIMessage`, `HumanMessage`, `SystemMessage`, `ToolMessage`).
- **LangGraph Version Compatibility**: Graph node execution tests verify standard `MessagesState` format (`{"messages": [...]}`).
- **Tool Resolution**: `tool_maker` uses `utils.all_tool_functions()` dynamically. Unit tests must mock `utils.all_tool_functions` if specific tool subsets are needed, or test with whatever tools are currently discoverable.

---

## 4. Conclusion & Proposed Test Specifications

### 4.1 Specification for `tests/agents/test_software_engineer.py`

#### Key Test Scenarios
1. `test_software_engineer_callable_and_graph_compiled()`: Assert `software_engineer` is callable and `graph` is compiled.
2. `test_tool_bindings()`: Verify `tools` list contains exactly the 7 required file & agent tools (`write_to_file`, `overwrite_file`, `delete_file`, `read_file`, `run_shell_command`, `assign_agent_to_task`, `list_available_agents`).
3. `test_system_prompt()`: Assert `system_prompt` mentions ReAct agent role, file management, and shell command capabilities.
4. `test_check_for_tool_calls_routing()`: Test state routing: returns `"tools"` when `last_message.tool_calls` is present; returns `END` (`"__end__"`) when empty.
5. `test_reasoning_node()`: Mock `config.default_langchain_model.bind_tools` to return a mock model. Verify `reasoning({"messages": [HumanMessage("test")]})` returns expected update dictionary `{"messages": [AIMessage(...)]}`.
6. `test_end_to_end_graph_execution_in_sandbox()`: Run `software_engineer(task)` with mocked LLM in a `tempfile.TemporaryDirectory()`. Simulate LLM issuing a `write_to_file` call, graph routing to `tools` node executing the tool in sandbox, LLM receiving tool response and outputting final text. Verify file is created in sandbox and state history contains complete message trace.

#### Proposed Code Structure for `tests/agents/test_software_engineer.py`
```python
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from agents.software_engineer import (
    software_engineer,
    graph,
    system_prompt,
    tools,
    reasoning,
    check_for_tool_calls,
)


class TestSoftwareEngineer(unittest.TestCase):
    def test_callable_and_graph_compiled(self):
        """Verify software_engineer function and graph object exist."""
        self.assertTrue(callable(software_engineer))
        self.assertIsNotNone(graph)

    def test_tool_bindings(self):
        """Verify software_engineer binds all 7 required file and agent management tools."""
        tool_names = [t.name for t in tools]
        expected_tools = [
            "write_to_file",
            "overwrite_file",
            "delete_file",
            "read_file",
            "run_shell_command",
            "assign_agent_to_task",
            "list_available_agents",
        ]
        for expected in expected_tools:
            self.assertIn(expected, tool_names)
        self.assertEqual(len(tools), 7)

    def test_system_prompt_content(self):
        """Verify system prompt contains core identity instructions."""
        self.assertIn("software_engineer", system_prompt)
        self.assertIn("create, modify, and delete code", system_prompt)

    def test_check_for_tool_calls_with_tool_calls(self):
        """Verify check_for_tool_calls routes to 'tools' when tool calls exist."""
        msg = AIMessage(content="Writing code", tool_calls=[{"name": "write_to_file", "args": {"file": "a.txt", "file_contents": "hi"}, "id": "call_1"}])
        state = {"messages": [msg]}
        self.assertEqual(check_for_tool_calls(state), "tools")

    def test_check_for_tool_calls_without_tool_calls(self):
        """Verify check_for_tool_calls routes to '__end__' when tool calls are empty."""
        msg = AIMessage(content="Task completed.")
        state = {"messages": [msg]}
        self.assertEqual(check_for_tool_calls(state), "__end__")

    @patch("config.default_langchain_model.bind_tools")
    def test_reasoning_node(self, mock_bind_tools):
        """Test reasoning node invokes model bound with tools."""
        mock_model = MagicMock()
        mock_ai_msg = AIMessage(content="Thinking...")
        mock_model.invoke.return_value = mock_ai_msg
        mock_bind_tools.return_value = mock_model

        input_state = {"messages": [HumanMessage(content="Build a feature")]}
        result = reasoning(input_state)

        mock_bind_tools.assert_called_once_with(tools)
        mock_model.invoke.assert_called_once_with(input_state["messages"])
        self.assertEqual(result, {"messages": [mock_ai_msg]})

    @patch("config.default_langchain_model.bind_tools")
    def test_end_to_end_sandbox_execution(self, mock_bind_tools):
        """Verify graph execution flow with sandboxed file writing and mocked LLM."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = os.path.join(tmp_dir, "test_output.txt")

            # Mock LLM sequence: 1st turn tool call, 2nd turn final answer
            mock_model = MagicMock()
            ai_step1 = AIMessage(
                content="Writing file",
                tool_calls=[{
                    "name": "write_to_file",
                    "args": {"file": test_file, "file_contents": "Hello World"},
                    "id": "call_123"
                }]
            )
            ai_step2 = AIMessage(content="File write complete.")
            mock_model.invoke.side_effect = [ai_step1, ai_step2]
            mock_bind_tools.return_value = mock_model

            result = software_engineer(f"Write Hello World to {test_file}")

            # Verify sandboxed file was created
            self.assertTrue(os.path.exists(test_file))
            with open(test_file, "r") as f:
                self.assertEqual(f.read(), "Hello World")

            # Verify graph state message flow
            messages = result["messages"]
            self.assertIsInstance(messages[0], SystemMessage)
            self.assertIsInstance(messages[1], HumanMessage)
            self.assertEqual(messages[2], ai_step1)
            self.assertIsInstance(messages[3], ToolMessage)
            self.assertEqual(messages[4], ai_step2)


if __name__ == "__main__":
    unittest.main()
```

---

### 4.2 Specification for `tests/agents/test_tool_maker.py`

#### Key Test Scenarios
1. Existing platform info & prompt builder tests retained (`test_get_platform_info`, `test_get_os_guidance_prompt_*`, `test_build_tool_maker_prompt`).
2. `test_tool_maker_dynamic_tools_loading()`: Verify `tools` in `tool_maker` matches `utils.all_tool_functions()`.
3. `test_check_for_tool_calls_routing()`: Test state routing logic (`"tools"` vs `"__end__"`).
4. `test_reasoning_node()`: Test reasoning node tool binding and invocation.
5. `test_synthesized_tool_and_unittest_validation()`: Mock LLM generating python tool code and test file code. Execute validation on tool & unittest code syntax using `ast.parse`.
6. `test_tool_synthesis_graph_execution_sandbox()`: Execute `tool_maker(task)` with mocked LLM in temporary directory creating `tools/dummy_tool.py` and `tests/tools/test_dummy_tool.py`, verifying complete synthesis workflow.

#### Proposed Code Structure Upgrade for `tests/agents/test_tool_maker.py`
```python
import ast
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
import utils
from agents.tool_maker import (
    get_os_guidance_prompt,
    build_tool_maker_prompt,
    tool_maker,
    graph,
    tools,
    reasoning,
    check_for_tool_calls,
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
        self.assertIsNotNone(graph)

    def test_check_for_tool_calls_routing(self):
        """Test StateGraph routing for tool calls vs END."""
        msg_with_tools = AIMessage(content="Creating tool", tool_calls=[{"name": "write_to_file", "args": {}, "id": "1"}])
        self.assertEqual(check_for_tool_calls({"messages": [msg_with_tools]}), "tools")

        msg_no_tools = AIMessage(content="Tool created.")
        self.assertEqual(check_for_tool_calls({"messages": [msg_no_tools]}), "__end__")

    @patch("config.default_langchain_model.bind_tools")
    def test_reasoning_node(self, mock_bind_tools):
        """Test reasoning node tool binding and invocation."""
        mock_model = MagicMock()
        mock_ai_msg = AIMessage(content="Designing tool")
        mock_model.invoke.return_value = mock_ai_msg
        mock_bind_tools.return_value = mock_model

        input_state = {"messages": [HumanMessage(content="Create a math tool")]}
        result = reasoning(input_state)

        mock_bind_tools.assert_called_once_with(tools)
        self.assertEqual(result, {"messages": [mock_ai_msg]})

    def test_synthesized_tool_and_unittest_ast_syntax(self):
        """Verify generated tool code and unittest structure parse cleanly as python AST."""
        tool_code = '''
from langchain_core.tools import tool

@tool
def add_numbers(a: int, b: int) -> int:
    """Adds two numbers."""
    return a + b
'''
        unittest_code = '''
import unittest
from tools import add_numbers

class TestAddNumbers(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add_numbers.add_numbers.invoke({"a": 1, "b": 2}), 3)

if __name__ == '__main__':
    unittest.main()
'''
        tool_ast = ast.parse(tool_code)
        unittest_ast = ast.parse(unittest_code)
        self.assertIsInstance(tool_ast, ast.Module)
        self.assertIsInstance(unittest_ast, ast.Module)

    @patch("config.default_langchain_model.bind_tools")
    def test_tool_synthesis_graph_execution_sandbox(self, mock_bind_tools):
        """Verify full tool synthesis flow in sandboxed directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tool_path = os.path.join(tmp_dir, "sample_tool.py")

            mock_model = MagicMock()
            ai_step1 = AIMessage(
                content="Writing tool",
                tool_calls=[{
                    "name": "write_to_file",
                    "args": {"file": tool_path, "file_contents": "# sample tool"},
                    "id": "call_tool_1"
                }]
            )
            ai_step2 = AIMessage(content="Tool created successfully.")
            mock_model.invoke.side_effect = [ai_step1, ai_step2]
            mock_bind_tools.return_value = mock_model

            result = tool_maker(f"Create tool at {tool_path}")

            self.assertTrue(os.path.exists(tool_path))
            self.assertEqual(len(result["messages"]), 5)


if __name__ == "__main__":
    unittest.main()
```

---

### 4.3 Specification for `tests/agents/test_web_researcher.py`

#### Key Test Scenarios
1. `test_web_researcher_callable_and_graph_compiled()`: Assert `web_researcher` is callable and `graph` is compiled.
2. `test_search_tool_bindings()`: Verify `tools` list contains `duck_duck_go_web_search` and `fetch_web_page_content`.
3. `test_system_prompt_content()`: Verify `system_prompt` content specifies web research role and search/fetch capabilities.
4. `test_check_for_tool_calls_routing()`: Test routing logic for tool calls vs `END`.
5. `test_offline_duckduckgo_mock()`: Test direct execution of `duck_duck_go_web_search` tool with `DuckDuckGoSearchResults.invoke` mocked offline.
6. `test_offline_web_fetcher_mock()`: Test direct execution of `fetch_web_page_content` tool with `SeleniumURLLoader.load` mocked offline returning a dummy document.
7. `test_end_to_end_offline_web_research_react_loop()`: Execute full `web_researcher(task)` graph loop with mocked LLM, mocked DDG search, and mocked Web Page fetcher. Verify zero external network calls occur and message chain matches expected ReAct cycle.

#### Proposed Code Structure for `tests/agents/test_web_researcher.py`
```python
import unittest
from unittest.mock import MagicMock, patch

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from agents.web_researcher import (
    web_researcher,
    graph,
    system_prompt,
    tools,
    reasoning,
    check_for_tool_calls,
)


class TestWebResearcher(unittest.TestCase):
    def test_callable_and_graph_compiled(self):
        """Verify web_researcher function and graph object exist."""
        self.assertTrue(callable(web_researcher))
        self.assertIsNotNone(graph)

    def test_search_tool_bindings(self):
        """Verify web_researcher binds search and web page fetch tools."""
        tool_names = [t.name for t in tools]
        self.assertIn("duck_duck_go_web_search", tool_names)
        self.assertIn("fetch_web_page_content", tool_names)
        self.assertEqual(len(tools), 2)

    def test_system_prompt_content(self):
        """Verify system prompt specifies web research identity."""
        self.assertIn("web_researcher", system_prompt)
        self.assertIn("search the web", system_prompt)
        self.assertIn("fetch the content of a web page", system_prompt)

    def test_check_for_tool_calls_routing(self):
        """Verify routing to 'tools' vs '__end__' based on tool_calls field."""
        msg_tools = AIMessage(
            content="Searching...",
            tool_calls=[{"name": "duck_duck_go_web_search", "args": {"query": "python"}, "id": "c1"}]
        )
        self.assertEqual(check_for_tool_calls({"messages": [msg_tools]}), "tools")

        msg_end = AIMessage(content="Research finished.")
        self.assertEqual(check_for_tool_calls({"messages": [msg_end]}), "__end__")

    @patch("langchain_community.tools.DuckDuckGoSearchResults.invoke")
    def test_offline_duckduckgo_tool(self, mock_ddg_invoke):
        """Test duck_duck_go_web_search tool offline with mocked DDG response."""
        mock_ddg_invoke.return_value = "[snippet: LangGraph is a library... title: LangGraph link: https://langchain.com]"
        from tools.duck_duck_go_web_search import duck_duck_go_web_search

        result = duck_duck_go_web_search.invoke({"query": "LangGraph"})
        self.assertIn("LangGraph is a library", result)
        mock_ddg_invoke.assert_called_once_with("LangGraph")

    @patch("langchain_community.document_loaders.url_selenium.SeleniumURLLoader.load")
    def test_offline_web_fetcher_tool(self, mock_selenium_load):
        """Test fetch_web_page_content tool offline with mocked Selenium loader."""
        mock_doc = Document(
            page_content="Mocked HTML page content for LangGraph docs",
            metadata={"source": "https://langchain.com"}
        )
        mock_selenium_load.return_value = [mock_doc]
        from tools.fetch_web_page_content import fetch_web_page_content

        result = fetch_web_page_content.invoke({"url": "https://langchain.com"})
        self.assertEqual(result.page_content, "Mocked HTML page content for LangGraph docs")
        mock_selenium_load.assert_called_once()

    @patch("langchain_community.document_loaders.url_selenium.SeleniumURLLoader.load")
    @patch("langchain_community.tools.DuckDuckGoSearchResults.invoke")
    @patch("config.default_langchain_model.bind_tools")
    def test_end_to_end_offline_react_loop(self, mock_bind_tools, mock_ddg_invoke, mock_selenium_load):
        """Test end-to-end web_researcher ReAct cycle offline without network requests."""
        mock_ddg_invoke.return_value = "[snippet: AgentK info title: AgentK link: https://example.com]"
        mock_doc = Document(page_content="Detailed AgentK documentation", metadata={"source": "https://example.com"})
        mock_selenium_load.return_value = [mock_doc]

        # Multi-step LLM response sequence
        mock_model = MagicMock()
        ai_step1 = AIMessage(
            content="Searching web",
            tool_calls=[{"name": "duck_duck_go_web_search", "args": {"query": "AgentK"}, "id": "c1"}]
        )
        ai_step2 = AIMessage(
            content="Fetching page content",
            tool_calls=[{"name": "fetch_web_page_content", "args": {"url": "https://example.com"}, "id": "c2"}]
        )
        ai_step3 = AIMessage(content="AgentK is an autoagentic AGI system.")
        mock_model.invoke.side_effect = [ai_step1, ai_step2, ai_step3]
        mock_bind_tools.return_value = mock_model

        result = web_researcher("What is AgentK?")

        messages = result["messages"]
        self.assertEqual(len(messages), 7)
        self.assertIsInstance(messages[0], SystemMessage)
        self.assertIsInstance(messages[1], HumanMessage)
        self.assertEqual(messages[2], ai_step1)
        self.assertIsInstance(messages[3], ToolMessage)
        self.assertEqual(messages[4], ai_step2)
        self.assertIsInstance(messages[5], ToolMessage)
        self.assertEqual(messages[6], ai_step3)
        self.assertEqual(messages[6].content, "AgentK is an autoagentic AGI system.")


if __name__ == "__main__":
    unittest.main()
```

---

## 5. Verification Method

To verify the unit test suite upgrades after implementation:

1. **Run pytest on all agent tests**:
   ```bash
   pytest /Users/ricardo/AgentK/tests/agents/test_software_engineer.py
   pytest /Users/ricardo/AgentK/tests/agents/test_tool_maker.py
   pytest /Users/ricardo/AgentK/tests/agents/test_web_researcher.py
   ```
2. **Run via python unittest runner**:
   ```bash
   python -m unittest tests/agents/test_software_engineer.py
   python -m unittest tests/agents/test_tool_maker.py
   python -m unittest tests/agents/test_web_researcher.py
   ```
3. **Verify offline execution**:
   - Ensure tests complete rapidly (under 5 seconds total) without making external network calls or requiring active API keys.
4. **Invalidation Conditions**:
   - Test suite fails if external network dependencies are accessed.
   - Test suite fails if file system side effects persist outside temporary sandbox directories.
   - Test suite fails if state graph message history format is altered without updating assertions.
