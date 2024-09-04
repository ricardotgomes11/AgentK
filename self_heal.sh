#!/bin/sh

LOG_FILE="/Users/rickyg/AgentK/self_heal.log"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a $LOG_FILE
}

# Function to check if WRITES_IDX_MAP exists
check_symbol() {
    python3 -c "from langgraph.checkpoint.base import WRITES_IDX_MAP" 2>/dev/null
    return $?
}

# Function to update the langgraph package
update_langgraph() {
    log_message "Updating langgraph package..."
    pip install --upgrade langgraph
    if [ $? -ne 0 ]; then
        log_message "Failed to update langgraph package. Exiting."
        exit 1
    fi
}

# Function to create a basic agent_kernel.py file if it doesn't exist
create_agent_kernel() {
    log_message "Creating a basic agent_kernel.py file..."
    cat <<EOF > /Users/rickyg/AgentK/agent_kernel.py
# Basic agent_kernel.py
def main():
    print("Hello, Agent Kernel!")

if __name__ == "__main__":
    main()
EOF
    if [ $? -ne 0 ]; then
        log_message "Failed to create agent_kernel.py. Exiting."
        exit 1
    fi
}

# Function to run the application
run_application() {
    if [ ! -f /Users/rickyg/AgentK/agent_kernel.py ]; then
        log_message "File /Users/rickyg/AgentK/agent_kernel.py not found. Creating it..."
        create_agent_kernel
    fi
    log_message "Running the application..."
    python3 /Users/rickyg/AgentK/agent_kernel.py
    if [ $? -ne 0 ]; then
        log_message "Application encountered an error. Exiting."
        exit 1
    fi
}

# Function to check and update dependencies
check_and_update_dependencies() {
    log_message "Checking and updating dependencies..."
    pip check
    if [ $? -ne 0 ]; then
        log_message "Dependencies are broken. Attempting to fix..."
        if [ ! -f /Users/rickyg/AgentK/requirements.txt ]; then
            log_message "requirements.txt not found. Exiting."
            exit 1
        fi
        pip install --upgrade --force-reinstall -r /Users/rickyg/AgentK/requirements.txt
        if [ $? -ne 0 ]; then
            log_message "Failed to fix dependencies. Exiting."
            exit 1
        fi
    fi
}

# Main script execution
log_message "Starting self-heal script..."

# Check if WRITES_IDX_MAP exists
if ! check_symbol; then
    log_message "WRITES_IDX_MAP not found. Updating langgraph package..."
    update_langgraph
fi

# Check and update dependencies
check_and_update_dependencies

# Run the application
run_application

log_message "Self-heal script completed successfully."#!/bin/sh

# Function to check if WRITES_IDX_MAP exists
check_symbol() {
    python3 -c "from langgraph.checkpoint.base import WRITES_IDX_MAP" 2>/dev/null
    return $?
}

# Function to update the langgraph package
update_langgraph() {
    echo "Updating langgraph package..."
    pip install --upgrade langgraph
    if [ $? -ne 0 ]; then
        echo "Failed to update langgraph package. Exiting."
        exit 1
    fi
}

# Function to create a basic agent_kernel.py file if it doesn't exist
create_agent_kernel() {
    echo "Creating a basic agent_kernel.py file..."
    cat <<EOF > /Users/rickyg/AgentK/agent_kernel.py
# Basic agent_kernel.py
def main():
    print("Hello, Agent Kernel!")

if __name__ == "__main__":
    main()
EOF
    if [ $? -ne 0 ]; then
        echo "Failed to create agent_kernel.py. Exiting."
        exit 1
    fi
}

# Function to run the application
run_application() {
    if [ ! -f /Users/rickyg/AgentK/agent_kernel.py ]; then
        echo "File /Users/rickyg/AgentK/agent_kernel.py not found. Creating it..."
        create_agent_kernel
    fi
    echo "Running the application..."
    python3 /Users/rickyg/AgentK/agent_kernel.py
    if [ $? -ne 0 ]; then
        echo "Application encountered an error. Exiting."
        exit 1
    fi
}

# Check if WRITES_IDX_MAP exists
if ! check_symbol; then
    echo "WRITES_IDX_MAP not found. Updating langgraph package..."
    update_langgraph
fi

# Run the application
run_application#!/bin/sh

# Function to check if WRITES_IDX_MAP exists
check_symbol() {
    python3 -c "from langgraph.checkpoint.base import WRITES_IDX_MAP" 2>/dev/null
    return $?
}

# Function to update the langgraph package
update_langgraph() {
    pip install --upgrade langgraph
}

# Function to run the application
run_application() {
    python3 /Users/rickyg/AgentK/agent_kernel.py
}

# Check if WRITES_IDX_MAP exists
if ! check_symbol; then
    echo "WRITES_IDX_MAP not found. Updating langgraph package..."
    update_langgraph
fi

# Run the application
echo "Running the application..."
run_application#!/bin/sh

# Function to check if WRITES_IDX_MAP exists
check_symbol() {
    python3 -c "from langgraph.checkpoint.base import WRITES_IDX_MAP" 2>/dev/null
    return $?
}

# Function to update the langgraph package
update_langgraph() {
    pip install --upgrade langgraph
}

# Function to run the application
run_application() {
    python3 /Users/rickyg/AgentK/agent_kernel.py
}

# Check if WRITES_IDX_MAP exists
if ! check_symbol; then
    echo "WRITES_IDX_MAP not found. Updating langgraph package..."
    update_langgraph
fi

# Run the application
echo "Running the application..."
run_application#!/bin/sh

# Function to check if WRITES_IDX_MAP exists
check_symbol() {
    python3 -c "from langgraph.checkpoint.base import WRITES_IDX_MAP" 2>/dev/null
    return $?
}

# Function to update the langgraph package
update_langgraph() {
    pip install --upgrade langgraph
}

# Function to run the application
run_application() {
    python3 /app/agent_kernel.py
}

# Check if WRITES_IDX_MAP exists
if ! check_symbol; then
    echo "WRITES_IDX_MAP not found. Updating langgraph package..."
    update_langgraph
fi

# Run the application
echo "Running the application..."
run_application
