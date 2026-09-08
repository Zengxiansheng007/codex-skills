# Ralph-Style Long Task Runtime Contract

Read this for a Story that may require multiple execution rounds.

## Reused Ralph L2 Modules

The system reuses Ralph L2 concepts for small work units, progress memory, completion indicators, circuit breaking and rate/resource limits. It adapts them so Codex, not the execution Agent, owns completion and HALF_OPEN reauthorization.

## Hard Limits

- Count only actual executor work as an execution round.
- Verified progress requires FR/AC mapping, passing validation, evidence and an improved governed state.
- Three consecutive execution rounds without verified progress open the circuit.
- The third identical failure fingerprint requires repair review; the fifth opens the circuit.
- The third invalid feedback with the same root cause opens the circuit.
- The first timeout permits one checkpointed recovery; a later timeout permits bounded Codex takeover only when preauthorized, otherwise it blocks.
- A Story may execute at most ten rounds. An eleventh round cannot start.
- HALF_OPEN requires Codex reauthorization and permits one probe.

Use Event History and Atomic Snapshot for every round. A stopReason selects a non-completed state.

Trace: FR-015 through FR-021, AC-010, AC-022 through AC-025.
