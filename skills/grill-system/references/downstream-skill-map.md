# Downstream Skill Map

Use this map after a grilling session reaches an exit criterion. The ledger's `phase`, `result`, `closureEvidence`, `writebackPolicy`, `protectedAssets`, `processArtifacts`, `exceptions`, `checkpoints`, and `writebackReceipts` control the transition; a report never substitutes for those records.

| Condition | Next skill | Output expected |
|---|---|---|
| terms or domain concepts were resolved during active review | domain-modeling | proposed glossary or ADR decisions returned to the Grill ledger; no immediate formal write |
| terms or domain concepts were resolved after eligible writeback | domain-modeling | centralized glossary or ADR update with a recorded receipt |
| requirement decisions are stable and closure-backed writeback is eligible | write-requirements-prd or to-spec | centralized PRD/spec batch |
| a receipt completes with outcome `no-op` | owning writer and reviewer | no formal content, version, metadata, or RTM change; retain the verified receipt as evidence |
| a receipt completes with outcome `updated` | owning writer and reviewer | retain actual file/hash evidence and proceed with normal downstream validation |
| result is conclusions-only, paused, blocked, repair-needed, partial-failure, or legacy-read-only | owning reviewer or user | no formal write; preserve ledger, writebackReceipts, recovery, and next action |
| work is ready to slice | to-tickets | tracer-bullet tickets |
| a state/UI/logic question cannot be settled in prose | prototype | throwaway answer artifact |
| a claim needs external evidence | research | cited HTML evidence report |
| execution should start | implement or ui-test | controlled implementation or test run |
| a failure needs a tight feedback loop | diagnosing-bugs | repro loop and root-cause path |
| the session is too long or branches | handoff | continuation document |
| the effort exceeds one session | wayfinder | map and investigation tickets |

## Do Not Route

- Do not route to implementation while P0 questions remain unresolved.
- Do not route to tickets when the destination itself is unclear.
- Do not route to prototype for questions that can be answered by reading existing code or docs.
- Do not route to research for decisions that belong to the user.
- Do not treat an old report, a per-question confirmation, a return from a callee, or a successful format check as closure or write authorization.
