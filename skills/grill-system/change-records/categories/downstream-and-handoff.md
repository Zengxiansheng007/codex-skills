# Downstream And Handoff Change Ledger

## Purpose

Record changes to handoff contracts, downstream skill routing, A2A packets, or feedback review boundaries.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-09-06 | CR-20260906-005 | V2 runtime and session/phase contracts | contract | Hand off only closure-backed batches with frozen plans and verify final receipts against actual hashes. | validated |
| 2026-09-06 | CR-20260906-001 | references/downstream-skill-map.md | governance | Route only closure-backed eligible results to formal writers; route all non-writing results to preservation or recovery. | validated |
| 2026-08-29 | CR-20260829-001 | references/grill-session-contract.md | updated | Session contract already documents required fields and status values; now backed by grill-session.schema.json. | validated-candidate |

## Detailed Records

### CR-20260906-005 - v2-batch-handoff-contract

- Section changed: V2 runtime plus session and phase contracts.
- Before: A downstream writer had no candidate contract for frozen decision content, scopes, planned expected hashes, actual receipt verification, or explicit no-op outcome.
- After: `begin-writeback --plan` freezes the handoff, and `verify-writeback` records actual hash evidence as `updated`, `no-op`, or failure/recovery.
- Why: FR-005, FR-009, FR-011, and AC-005, AC-009, AC-011 require result-aware downstream behavior.
- Impact: A report, returned call, or outer exit code cannot become writeback authorization or completion evidence.
- Validation: Pending root final suite and independent junction evidence.
- Detail record: ../entries/2026/2026-09/CR-20260906-005-v2-runtime-artifact-boundary.md

### CR-20260906-001 - closure-backed-downstream-routing

- Section changed: references/downstream-skill-map.md.
- Before: Stable decisions could be read as a sufficient route condition.
- After: The map requires closure evidence and an eligible result before centralized formal writing; all other outcomes preserve state or request recovery.
- Why: FR-005, FR-008, FR-009, and FR-012 require return-state-aware routing.
- Impact: Legacy reports remain read-only and no downstream route can infer write authority from report existence.
- Validation: Pending candidate structure, change-record, and runtime behavior checks.
- Detail record: ../entries/2026/2026-09/CR-20260906-001-phase-boundary-cross-skill-documentation.md

### CR-20260829-001 - grill-downstream-contract

- Section changed: references/grill-session-contract.md, schemas/grill-session.schema.json.
- Before: The session contract was a Markdown reference only; no machine-readable schema enforced it.
- After: The grill-session.schema.json formalizes the contract; the failure classification provides stable routing identifiers for downstream skills.
- Why: Downstream skills (handoff, development-system) need stable failure class names to route grill sessions without ambiguity.
- Impact: Future downstream skill updates can reference the grill failure classes as stable identifiers.
- Detail record: ../entries/2026/2026-08/CR-20260829-001-grill-strong-gate.md
