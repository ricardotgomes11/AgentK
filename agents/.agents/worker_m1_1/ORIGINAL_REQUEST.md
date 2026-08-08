## 2026-07-25T20:48:25Z
MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You are the Worker for Milestone 1: Control Plane & Path Portability.
Your working directory for metadata is: /Users/ricardo/AgentK/agents/.agents/worker_m1_1

Tasks to implement:
1. Refactor /Users/ricardo/AgentK/agents/sovereign_gate.py:
   - Read specifications in /Users/ricardo/AgentK/agents/.agents/explorer_m1_1/handoff.md.
   - Replace all hardcoded absolute paths (/Users/ricardo/AgentK/...) in PROTECTED_PATHS, is_protected_path(), and _is_agent_or_tool_write() with dynamic project root path resolution:
     PROJECT_ROOT = (Path(os.environ.get("AGENTK_ROOT")).resolve() if os.environ.get("AGENTK_ROOT") else Path(__file__).resolve().parents[1])
   - Canonicalize paths using Path.resolve() for symlink and traversal protection.
   - Refactor git directory and agent/tool directory containment checks.
   - Update _deny_dangerous_commands regex to reliably catch destructive commands referencing protected keywords.

2. Refactor /Users/ricardo/AgentK/agents/agent_smith.py:
   - Read specifications in /Users/ricardo/AgentK/agents/.agents/explorer_m1_2/handoff.md.
   - Remove top-level relative file open strings ("agents/web_researcher.py" and "tests/agents/test_web_researcher.py").
   - Define BASE_DIR = Path(__file__).resolve().parent.parent.
   - Implement helper functions load_agent_template(example_agent="web_researcher", base_dir=None) and get_system_prompt(example_agent="web_researcher", base_dir=None).
   - Ensure system_prompt is constructed via get_system_prompt() to guarantee CWD independence when importing or running agent_smith.

3. Refactor /Users/ricardo/AgentK/utils.py and /Users/ricardo/AgentK/agents/tool_maker.py:
   - Read specifications in /Users/ricardo/AgentK/agents/.agents/explorer_m1_3/handoff.md.
   - In utils.py: Add get_platform_info() helper to dynamically detect host OS platform and package manager.
   - In agents/tool_maker.py: Replace static hardcoded Debian 11 system_prompt string with dynamic prompt builders get_os_guidance_prompt(os_context=None) and build_tool_maker_prompt(os_context=None). Update tool_maker(task: str, os_context: str | dict | None = None).

4. Create Unit Tests:
   - Implement /Users/ricardo/AgentK/tests/agents/test_sovereign_gate.py covering path resolution, env override, protected paths canonicalization, is_protected_path (exact, traversal, symlinks, .git), _is_agent_or_tool_write, _deny_dangerous_commands, and get_sovereign_policies.
   - Implement /Users/ricardo/AgentK/tests/agents/test_agent_smith.py covering callable interface, template loading, get_system_prompt, CWD independence (os.chdir), and check_for_tool_calls routing logic.

5. Verify Implementation:
   - Run python3 -m unittest discover -s tests
   - Run pytest tests/agents/
   - Document build/test commands and output in your handoff report.

Write your handoff report to /Users/ricardo/AgentK/agents/.agents/worker_m1_1/handoff.md and send a message back when done.
