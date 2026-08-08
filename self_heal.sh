#!/bin/sh
# ============================================================================
# AgentK Self-Heal Script
# Checks dependencies, repairs broken state, and bootstraps the system.
# ============================================================================

AGENTK_ROOT="/Users/ricardo/AgentK"
LOG_FILE="${AGENTK_ROOT}/self_heal.log"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------
check_langgraph_symbol() {
    python3 -c "from langgraph.checkpoint.base import WRITES_IDX_MAP" 2>/dev/null
    return $?
}

check_sdk() {
    python3 -c "from google.antigravity import Agent" 2>/dev/null
    return $?
}

check_bridge() {
    python3 -c "
import sys; sys.path.insert(0, '${AGENTK_ROOT}'); sys.path.insert(0, '${AGENTK_ROOT}/agents')
from sdk_bridge import get_system_prompt
prompt = get_system_prompt()
assert len(prompt) > 0, 'Empty system prompt'
" 2>/dev/null
    return $?
}

# ---------------------------------------------------------------------------
# Repair actions
# ---------------------------------------------------------------------------
update_langgraph() {
    log_message "Updating langgraph package..."
    pip3 install --upgrade langgraph
    if [ $? -ne 0 ]; then
        log_message "FAILED: Could not update langgraph."
        return 1
    fi
}

install_sdk() {
    log_message "Installing google-antigravity SDK..."
    pip3 install google-antigravity
    if [ $? -ne 0 ]; then
        log_message "FAILED: Could not install google-antigravity SDK."
        return 1
    fi
}

check_and_update_dependencies() {
    log_message "Checking pip dependencies..."
    pip3 check 2>/dev/null
    if [ $? -ne 0 ]; then
        log_message "Dependencies broken. Reinstalling from requirements.txt..."
        if [ ! -f "${AGENTK_ROOT}/requirements.txt" ]; then
            log_message "FAILED: requirements.txt not found."
            return 1
        fi
        pip3 install --upgrade --force-reinstall -r "${AGENTK_ROOT}/requirements.txt"
        if [ $? -ne 0 ]; then
            log_message "FAILED: Could not repair dependencies."
            return 1
        fi
    fi
}

create_agent_kernel_fallback() {
    log_message "Creating fallback agent_kernel.py..."
    cat <<'EOF' > "${AGENTK_ROOT}/agent_kernel.py"
# Fallback agent_kernel.py — created by self_heal.sh
from dotenv import load_dotenv
load_dotenv()
from agents import hermes
from uuid import uuid4
hermes.hermes(str(uuid4()))
EOF
}

# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------
log_message "========================================="
log_message "AgentK self-heal starting..."
log_message "========================================="

# 1. Check langgraph
if ! check_langgraph_symbol; then
    log_message "WRITES_IDX_MAP not found. Updating langgraph..."
    update_langgraph
fi

# 2. Check SDK
if ! check_sdk; then
    log_message "Antigravity SDK not found. Installing..."
    install_sdk
fi

# 3. Check dependencies
check_and_update_dependencies

# 4. Check bridge
if ! check_bridge; then
    log_message "WARNING: SDK bridge failed to load. Agents may not be discoverable."
fi

# 5. Ensure entry point exists
if [ ! -f "${AGENTK_ROOT}/agent_kernel.py" ]; then
    log_message "agent_kernel.py missing. Creating fallback..."
    create_agent_kernel_fallback
fi

# 6. Run
log_message "Launching AgentK..."
cd "${AGENTK_ROOT}"
python3 "${AGENTK_ROOT}/agent_kernel.py"
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    log_message "AgentK exited with code ${EXIT_CODE}."
else
    log_message "AgentK session ended cleanly."
fi

log_message "Self-heal script completed."
