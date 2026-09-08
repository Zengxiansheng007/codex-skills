# Multi-Agent Concurrency Contract

Read this before enabling more than one live execution Agent.

Each concurrent Story receives an execution slot with a unique workspace fingerprint, permission policy, baseline fingerprint, Agent identity, write set, heartbeat and evidence set. `schedule_slots` blocks unmet dependencies, shared workspaces and overlapping write sets.

Codex alone schedules, pauses and merges slots. Before merge, `evaluate_merge` requires an unchanged baseline, no write-set conflict, passing validation, evidence and Story/FR/AC trace. A blocked slot cannot donate permissions, feedback or evidence to another slot.

Parallelism is optional. Use serial execution when Story independence, workspace isolation or merge evidence is uncertain.

Trace: FR-001, FR-007, FR-022, FR-028, FR-029, NFR-005, AC-026 through AC-028.
