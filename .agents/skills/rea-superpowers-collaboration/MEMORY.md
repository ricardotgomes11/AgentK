# Collaboration Memory Contract

This file defines a memory schema; it is not physical RAM, a running daemon, or a record that workers have executed. Do not store secrets, credentials, personal datasets, or raw sensitive target content here.

## Repository anchors
Repository: ricardotgomes11/AgentK. Inspected branch: hermes-agentic-flow. Reinspect the current commit before acting. agent_kernel.py bootstraps an Antigravity agent. agents/sdk_bridge.py defines inventory helpers and synchronous dispatch_agent. SDK tool registration, concurrency safety, and runtime availability are not established by those definitions alone.

## Volatile run state
Keep run_id, base_commit, target identity, approved scope, obligation states, task ownership, dispatch receipts, timeouts, cancellation state, evidence references, review findings, and acceptance decision in coordinator-owned run state. Workers return messages; they do not mutate shared state. Reduce results deterministically. Actual RAM-only storage must be verified rather than inferred from a TMPDIR pathname.

## Durable checkpoint
Persist only authorized, minimized checkpoints. Record schema version, run identity, source commit, evidence digests, pending tasks, and review status. Separate incomplete diagnostics from accepted reconstruction records. Stage a complete checkpoint before publishing it. Document storage and crash-durability assumptions.

## Resume
Verify the repository commit, target digest, runtime, outstanding authorization, and evidence references before resuming. Invalidate stale conclusions. Do not replay external writes automatically. Preserve completed evidence and choose the next operation from missing information rather than repeating an unchanged failed command.

## Truth states
planned -> dispatched -> observed -> validated -> accepted. Failure is retained as evidence with a next-route decision. Never promote a state merely because a document or JSON envelope exists.
