# CLW PH-2 Serial Orchestration Contract

This contract is scoped to `CLW-PH-2`; it is not the historical DSCR PH-2 approval phase.

## Entry Gate

Implementation and live acceptance require the PH-1 CompletionEvaluator to pass. Static contract preparation may be validated earlier, but it cannot make PH-2 `completed`.

## Queue And Selection

- Validate unique Story IDs, known dependencies, acyclic edges and non-empty FR/AC mappings before selection.
- Keep at most one active Story. Select only Stories whose dependencies passed the Codex Story completion gate.
- Sort eligible Stories by descending explicit priority and then stable Story ID.
- A blocked, failed, review-pending or evidence-incomplete dependency blocks downstream execution.

## Durable Progress

- Reuse hash-linked Event History and Atomic Snapshot. Persist the event before replacing the aggregate snapshot.
- Bind the snapshot to Anchor/version, Phase, workspace and canonical queue fingerprint.
- Resume fails closed on any identity, history, snapshot, queue or heartbeat mismatch.
- A passed Story is never re-executed during resume.

## Stop And Completion

- Reuse the Ralph L2-derived circuit, resource and failure budgets from `long-task-runtime-contract.md`.
- Queue empty, timeout, circuit OPEN, resource exhaustion or Agent completion claim never imply Phase completion.
- Phase completion requires every Story and AC, valid feedback, complete evidence, QA, drift, permission, risk and Codex review gates.

Trace: FR-CLW2-001 through FR-CLW2-010; AC-CLW2-001 through AC-CLW2-014.
