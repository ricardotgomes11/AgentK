import os
import subprocess
import time
from types import SimpleNamespace
from agents import sovereign_gate

# The Constant: The Ledger Path
LEDGER_PATH = os.path.expanduser('~/AgentK/nexus_ledger/execution.log')

def execute_task(task_command):
    tc = SimpleNamespace(
        name="run_command",
        args={"CommandLine": task_command, "command": task_command},
        canonical_path=None,
    )
    eval_result = sovereign_gate.evaluate_or_dispatch(tc)
    if getattr(eval_result, "denied", False):
        print(f"[SOVEREIGN GATE DENIED] Controller task blocked: {task_command}")
        return "Command denied by Sovereign Gate policy."

    result = subprocess.run(task_command, shell=True, capture_output=True, text=True)
    return result.stdout

def reconcile_state():
    with open(LEDGER_PATH, 'r') as f:
        # Pull the last intent
        lines = f.readlines()
        if lines:
            intent = lines[-1].strip()
            print(f"Reconciling Constant: {intent}")
            # Map the intent to local primitive actions
            if "SYNC" in intent:
                # Direct call to the driver
                execute_task("/Users/ricardo/.local/bin/cua-driver check_permissions")

if __name__ == "__main__":
    while True:
        reconcile_state()
        time.sleep(10) # Deterministic polling interval
