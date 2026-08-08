# Handoff Report: Explorer 2 (Milestone 2 - Prompt & Syntax Quality Fixes)

## Executive Summary
This investigation analyzed system prompts, docstrings, and string formatting across all agent modules in AgentK (`/Users/ricardo/AgentK/agents/`).
Key findings include:
1. **Unclosed Triple Backtick**: `web_researcher.py` (line 12) ends its `system_prompt` with an unclosed triple backtick (`` ``` ``). This causes raw markdown syntax corruption in LLM prompts and breaks codeblock formatting when `agent_smith.py` loads `web_researcher.py` as a dynamic example template.
2. **Typos & Missing Prepositions in System Prompts**:
   - `tool_maker.py`: Typo `succintly` (line 77), missing `for` in `"stands kernel"` (line 55), missing `to` in `"message the user"` (line 63), `eg.` instead of `e.g.` (line 85), typo `asccii` (line 94).
   - `agent_smith.py`: Missing `for` in `"stands kernel"` (line 41), missing `to` in `"message the user"` (line 49).
   - `hermes.py`: Missing `for` in `"stands kernel"` (line 18), duplicate step number `4.` (line 35), missing `of` in docstring `"activities agents"` (line 113), British spelling `optimise` (line 40).
   - `sdk_bridge.py`: British spelling `optimise` (line 94).

---

## 1. Observation

### 1.1 `web_researcher.py` (`/Users/ricardo/AgentK/agents/web_researcher.py`)
- **Lines 9–13**:
```python
9: system_prompt = """You are web_researcher, a ReAct agent that can use the web to research answers.
10: 
11: You have a tool to search the web, and a tool to fetch the content of a web page.
12: ```
13: """
```
Line 12 contains a standalone triple backtick `` ``` `` without any matching opening codeblock tag prior to it in the `system_prompt` string.

### 1.2 `tool_maker.py` (`/Users/ricardo/AgentK/agents/tool_maker.py`)
- **Line 55**:
  `The "K" stands kernel, meaning small core. The aim is for AgentK to be the minimum set of agents and tools necessary for it to bootstrap itself and then grow its own mind.`
  (Missing preposition `for` after `stands`).
- **Line 63**:
  `Else, your response is a message the user.  `
  (Missing preposition `to` after `message`, plus trailing spaces).
- **Line 77**:
  `When writing a tool, make sure to include a docstring on the function that succintly describes what the tool does.`
  (Typo `succintly` instead of `succinctly`).
- **Line 85**:
  `If you need human input to finish a tool (eg. you need them to sign up for an account and provide an API key) use the request_human_input tool.`
  (Typo `eg.` instead of `e.g.`).
- **Line 94**:
  `    """Adds an asccii face to the end of the supplied text."""`
  (Typo `asccii` instead of `ASCII` / `ascii`).

### 1.3 `agent_smith.py` (`/Users/ricardo/AgentK/agents/agent_smith.py`)
- **Line 41**:
  `The "K" stands kernel, meaning small core. The aim is for AgentK to be the minimum set of agents and tools necessary for it to bootstrap itself and then grow its own mind.`
  (Missing preposition `for`).
- **Line 49**:
  `Else, your response is a message the user.`
  (Missing preposition `to`).
- **Lines 74–77**:
```python
74: agents/{example_agent}.py
75: ```
76: {agent_code}
77: ```
```
Because line 90 sets `example_agent = "web_researcher"`, `load_agent_template` reads `web_researcher.py` and substitutes `{agent_code}`. Since `web_researcher.py` line 12 has `` ``` ``, `{agent_code}` inserts a triple backtick in the middle of line 76, terminating line 75's code block early and rendering line 77 as a orphaned backtick block.

### 1.4 `hermes.py` (`/Users/ricardo/AgentK/agents/hermes.py`)
- **Line 18**:
  `The "K" stands kernel, meaning small core. The aim is for AgentK to be the minimum set of agents and tools necessary for it to bootstrap itself and then grow its own mind.`
  (Missing preposition `for`).
- **Lines 30–35**:
```python
30: You interact with a user in this specific order:
31: 1. Reach a shared understanding on a goal.
32: 2. Think of a detailed sequential plan for how to achieve the goal through the orchestration of agents.
33: 3. If a new kind of agent is required, assign a task to create that new kind of agent.
34: 4. Assign agents and coordinate their activity based on your plan.
35: 4. Respond to the user once the goal is achieved or if you need their input.
```
  (Line 35 duplicates step number `4.` instead of step `5.`).
- **Line 40**:
  `Try to come up with agent roles that optimise for composability and future re-use, their roles should not be unreasonably specific.`
  (Spelling `optimise` vs American English standard `optimize`).
- **Line 113**:
  `    """The orchestrator that interacts with the user to understand goals, plan out how agents can meet the goal, assign tasks, and coordinate the activities agents."""`
  (Missing preposition `of` in `"activities agents"`).

### 1.5 `sdk_bridge.py` (`/Users/ricardo/AgentK/agents/sdk_bridge.py`)
- **Line 94**:
  `Design agent roles that optimise for composability and future re-use.`
  (Spelling `optimise` vs American English standard `optimize`).

---

## 2. Logic Chain

1. **Unclosed Backtick in `web_researcher.py`**:
   - `web_researcher.py` defines `system_prompt` on lines 9–13.
   - Line 12 contains `` ``` `` without a matching opening `` ``` `` in the prompt string.
   - When fed to an LLM, the model sees an unclosed markdown block, causing unpredictable model output formatting.
   - Furthermore, `agent_smith.py` imports `web_researcher.py` verbatim via `load_agent_template("web_researcher")` and formats it inside a markdown block:
     ```python
     agents/{example_agent}.py
     ```
     {agent_code}
     ```
     ```
   - Inserting `web_researcher.py`'s line 12 (`` ``` ``) prematurely closes `agent_smith`'s example code block, causing prompt syntax corruption in `agent_smith.py`.
   - **Conclusion**: Removing line 12 from `web_researcher.py` fixes both `web_researcher` prompt syntax and `agent_smith` template expansion.

2. **Typo & Grammar Fixes**:
   - `succintly` -> `succinctly` in `tool_maker.py:77`.
   - `"stands kernel"` -> `"stands for kernel"` in `tool_maker.py:55`, `agent_smith.py:41`, and `hermes.py:18`.
   - `"message the user"` -> `"message to the user"` in `tool_maker.py:63` and `agent_smith.py:49`.
   - `"eg."` -> `"e.g.,"` in `tool_maker.py:85`.
   - `"asccii"` -> `"ASCII"` in `tool_maker.py:94`.
   - Step sequence `4.` duplicate in `hermes.py:35` -> `5.`.
   - `"activities agents"` -> `"activities of agents"` in `hermes.py:113`.
   - `"optimise"` -> `"optimize"` in `hermes.py:40` and `sdk_bridge.py:94`.

---

## 3. Caveats
- `software_engineer.py` and `sovereign_gate.py` were reviewed and found to have clear, typo-free system prompts and docstrings.
- Python double curly braces (`{{` and `}}`) in `tool_maker.py` lines 106 and 131 are inside an `f"""..."""` multiline string. They are intentionally escaped python curly braces for literal dictionary generation in test example code strings and should NOT be modified.

---

## 4. Conclusion & Recommended Corrections

Below are the exact line-by-line replacement chunks recommended for implementation:

### 4.1 `/Users/ricardo/AgentK/agents/web_researcher.py`
**Target lines 9–13**:
```python
<<<< Current (lines 9-13)
system_prompt = """You are web_researcher, a ReAct agent that can use the web to research answers.

You have a tool to search the web, and a tool to fetch the content of a web page.
```
"""
==== Recommended
system_prompt = """You are web_researcher, a ReAct agent that can use the web to research answers.

You have a tool to search the web, and a tool to fetch the content of a web page.
"""
>>>>
```

### 4.2 `/Users/ricardo/AgentK/agents/tool_maker.py`
**Target lines 55, 63, 77, 85, 94**:
```python
<<<< Current Line 55
The "K" stands kernel, meaning small core. The aim is for AgentK to be the minimum set of agents and tools necessary for it to bootstrap itself and then grow its own mind.
==== Recommended Line 55
The "K" stands for kernel, meaning small core. The aim is for AgentK to be the minimum set of agents and tools necessary for it to bootstrap itself and then grow its own mind.
>>>>

<<<< Current Line 63
Else, your response is a message the user.  
==== Recommended Line 63
Else, your response is a message to the user.
>>>>

<<<< Current Line 77
When writing a tool, make sure to include a docstring on the function that succintly describes what the tool does.
==== Recommended Line 77
When writing a tool, make sure to include a docstring on the function that succinctly describes what the tool does.
>>>>

<<<< Current Line 85
If you need human input to finish a tool (eg. you need them to sign up for an account and provide an API key) use the request_human_input tool.
==== Recommended Line 85
If you need human input to finish a tool (e.g., you need them to sign up for an account and provide an API key) use the request_human_input tool.
>>>>

<<<< Current Line 94
    """Adds an asccii face to the end of the supplied text."""
==== Recommended Line 94
    """Adds an ASCII face to the end of the supplied text."""
>>>>
```

### 4.3 `/Users/ricardo/AgentK/agents/agent_smith.py`
**Target lines 41, 49**:
```python
<<<< Current Line 41
The "K" stands kernel, meaning small core. The aim is for AgentK to be the minimum set of agents and tools necessary for it to bootstrap itself and then grow its own mind.
==== Recommended Line 41
The "K" stands for kernel, meaning small core. The aim is for AgentK to be the minimum set of agents and tools necessary for it to bootstrap itself and then grow its own mind.
>>>>

<<<< Current Line 49
Else, your response is a message the user.
==== Recommended Line 49
Else, your response is a message to the user.
>>>>
```

### 4.4 `/Users/ricardo/AgentK/agents/hermes.py`
**Target lines 18, 35, 40, 113**:
```python
<<<< Current Line 18
The "K" stands kernel, meaning small core. The aim is for AgentK to be the minimum set of agents and tools necessary for it to bootstrap itself and then grow its own mind.
==== Recommended Line 18
The "K" stands for kernel, meaning small core. The aim is for AgentK to be the minimum set of agents and tools necessary for it to bootstrap itself and then grow its own mind.
>>>>

<<<< Current Line 35
4. Respond to the user once the goal is achieved or if you need their input.
==== Recommended Line 35
5. Respond to the user once the goal is achieved or if you need their input.
>>>>

<<<< Current Line 40
Try to come up with agent roles that optimise for composability and future re-use, their roles should not be unreasonably specific.
==== Recommended Line 40
Try to come up with agent roles that optimize for composability and future re-use, their roles should not be unreasonably specific.
>>>>

<<<< Current Line 113
    """The orchestrator that interacts with the user to understand goals, plan out how agents can meet the goal, assign tasks, and coordinate the activities agents."""
==== Recommended Line 113
    """The orchestrator that interacts with the user to understand goals, plan out how agents can meet the goal, assign tasks, and coordinate the activities of agents."""
>>>>
```

### 4.5 `/Users/ricardo/AgentK/agents/sdk_bridge.py`
**Target line 94**:
```python
<<<< Current Line 94
Design agent roles that optimise for composability and future re-use.
==== Recommended Line 94
Design agent roles that optimize for composability and future re-use.
>>>>
```

---

## 5. Verification Method

To verify these findings and the recommended prompt fixes:

1. **Verify `web_researcher.py` Prompt String**:
   - Inspect `agents/web_researcher.py` lines 9–13. Confirm line 12 has `` ``` ``.
   - Run python to check prompt string:
     `python3 -c "from agents.web_researcher import system_prompt; print(repr(system_prompt))"`
     Verify string ends cleanly without trailing triple backticks.

2. **Verify `agent_smith.py` Template Expansion**:
   - Run python to test `get_system_prompt()`:
     `python3 -c "from agents.agent_smith import get_system_prompt; prompt = get_system_prompt(); print(prompt)"`
     Verify that codeblock backticks do not close unexpectedly inside example section.

3. **Verify Unit Test Suite**:
   - Run unit test suite:
     `pytest tests/agents/`
   - All agent tests should pass cleanly.
