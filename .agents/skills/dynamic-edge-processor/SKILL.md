---
name: dynamic-edge-processor
description: >-
  Closed-loop, zero-human-in-the-loop (Zero-HITL) recursive self-evolving edge processor. Ingests execution telemetry as fuel to dynamically synthesize tools, patch graph edges, auto-repair checkpoints, and elevate system capability without human intervention.
---

# Dynamic Edge Processor (`dynamic-edge-processor`)

## Overview
The `dynamic-edge-processor` skill enables AgentK to operate as an autonomous, self-healing, closed-loop system. Rather than relying on static agent flows or requiring interactive human authorization (`y/N`), this skill operates directly on dynamic graph edges, event-driven state transitions, and automated telemetry ingestion.

---

## Architectural Layers

1. **Silicon Layer (Dynamic Edge Engine)**
   - Evaluates state telemetry vectors (error rates, execution latency, context sizes).
   - Dynamically routes subtasks to appropriate agent nodes (`hermes`, `agent_smith`, `tool_maker`, `software_engineer`, `web_researcher`).

2. **Expansion Layer (Reactive Event Daemon)**
   - Asynchronous, non-blocking daemon loop (`scripts/edge_daemon.py`).
   - Uses `asyncio` and SQLite Write-Ahead Logging (`checkpoints.sqlite-wal`) for zero-latency background task processing.

3. **Substrate Layer (Isolated Checkpoint Branching)**
   - Automatic state graph forking and merging for self-healing error recovery against `checkpoints.sqlite`.
   - Automatic WAL checkpoint flushes and database integrity repair.

4. **Gold Metal Layer (Policy Pre-Attestation)**
   - Pre-attested security policy rules within `sovereign_gate.py`.
   - Safe, non-destructive code synthesis, test execution, and dynamic graph re-compilation are pre-cleared for Zero-HITL autonomous evolution.

---

## Dependencies
- `agents/sovereign_gate.py`
- `agents/agent_smith.py`
- `agents/tool_maker.py`
- `tools/assign_agent_to_task.py`
- `utils.py`
- `config.py`

---

## Quick Start

### 1. Check Daemon Status
```bash
python3 .agents/skills/dynamic-edge-processor/scripts/edge_daemon.py status
```

### 2. Run Self-Diagnostic Verification
```bash
python3 .agents/skills/dynamic-edge-processor/scripts/edge_daemon.py test --output /tmp/edge_daemon_test.json
```

### 3. Run Single Closed-Loop Evolution Cycle
```bash
python3 .agents/skills/dynamic-edge-processor/scripts/edge_daemon.py evolve
```

### 4. Trigger Automatic Checkpoint & DB Repair
```bash
python3 .agents/skills/dynamic-edge-processor/scripts/edge_daemon.py heal
```

### 5. Launch Continuous Background Daemon
```bash
python3 .agents/skills/dynamic-edge-processor/scripts/edge_daemon.py start
```

---

## Utility Scripts

### `scripts/edge_daemon.py`
Multi-command CLI script powering the dynamic edge processor:

- `start`: Launches continuous background processing loop with PID watchdog auto-restart.
- `status`: Queries daemon health, active agent/tool inventories, SQLite WAL status, and self-evolution metrics.
- `route`: Evaluates dynamic edge routing decision for a given task state vector.
- `evolve`: Ingests runtime telemetry/logs, detects missing capabilities or failures, and triggers synthesis cycles.
- `heal`: Performs SQLite database integrity checks, WAL cleanup, and checkpoint recovery.
- `stop`: Gracefully terminates the background daemon via signal handlers (`SIGTERM`, `SIGINT`).
- `test`: Verifies daemon loop mechanics, policy pre-attestation, and tool discovery.

---

## Rate Limiting & Resource Management
- Monitors execution frequency and enforces file-lock based rate limiting.
- Respects `assign_agent_to_task.MAX_DEPTH` recursion limits (default: 3) to prevent agent fork bombs.
- Emits structured JSON metrics to `--output` files.

---

## Common Pitfalls
1. **Hardcoding Tool/Agent Names**: Always discover live system capabilities dynamically using `utils.list_tools()` and `utils.list_agents()`.
2. **Interactive Blocking in Background Loops**: Never invoke blocking `input()` calls in background daemon mode; rely on `sovereign_gate` policy pre-attestation.
3. **Database Locks**: Always execute SQLite operations using WAL mode (`PRAGMA journal_mode=WAL;`) and close connections promptly.
