# Event History And Recovery Contract

Read this before starting, resuming or checkpointing a long task.

## Durable State

- Append every governed event with a monotonic `sequenceIndex`, `previousHash`, `eventHash`, timestamp, actor, FR/AC trace and evidence references.
- Write an Atomic Snapshot only after its corresponding event is durable.
- The snapshot records Anchor ID/version, workspace fingerprint, last event sequence/hash, Phase, Story, Round, counters, heartbeat, evidence and next action.
- Use `append_event`, `validate_history` and `write_snapshot_atomic`; never rewrite old history.

## Resume Gate

`resume_cycle` allows recovery only when Event History is valid and the snapshot hash, Anchor ID/version, workspace fingerprint, last sequence/hash and heartbeat all match. Any mismatch returns `blocked-external-dependency`; repair or requirements review is required before execution resumes.

Timeout, stop or process exit is not completion. Preserve partial evidence and counters before recovery or takeover.

Trace: FR-021, FR-031, AC-008, AC-022, AC-024.
