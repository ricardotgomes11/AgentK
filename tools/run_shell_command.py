import subprocess
from types import SimpleNamespace
from langchain_core.tools import tool
from agents import sovereign_gate

@tool
def run_shell_command(command: str):
    """Run a shell command and return the output."""
    tc = SimpleNamespace(
        name="run_shell_command",
        args={"command": command, "CommandLine": command},
        canonical_path=None,
    )
    eval_result = sovereign_gate.evaluate_or_dispatch(tc)
    if getattr(eval_result, "denied", False):
        print(f"[SOVEREIGN GATE DENIED] Command blocked: {command}")
        return {
            "stdout": "",
            "stderr": f"Command denied by Sovereign Gate policy: {command}",
            "returncode": 126,
            "denied": True,
        }

    print(f"Running shell command: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return { "stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode }