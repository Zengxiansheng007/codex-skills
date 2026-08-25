# CR-20260822-002 - Source Case And IR Contracts

| Field | Value |
|---|---|
| Status | applied |
| Target Skill | ui-test |
| Story | PH01-ST02 |
| Requirements | FR-CASE-002, FR-CASE-035..038 |
| Acceptance | AC-CASE-001, AC-CASE-002, AC-CASE-017 |

## Summary

Add Draft 2020-12 schemas for Source Case, Case IR and Resolved IR. Add RFC 8785 canonical bytes/hash, deterministic Source Case validation and lowering to Case IR. Activate the three contracts while leaving Compile Receipt planned for PH02-ST04.

## Context And Problem

Multiple human and automation copies lacked a unique case truth.

## Sections Changed

Source Case, Case IR, Resolved IR schemas and lowering code.

## Decision And Alternatives

Generate all views from one canonical source instead of synchronizing hand-written copies.

## Impact Analysis

Business changes now have one source hash and deterministic derivatives.

## Boundary

No renderer, release publisher, global Skill, D-drive asset or private UI behavior is included.

## Validation Evidence

- All three schemas parse and pass `Draft202012Validator.check_schema`.
- Source Case positive and negative contract tests pass.
- RFC 8785 hash is stable under object-key reordering and changes when a business value changes.
- Full candidate `ui-test` suite: 53 tests passed.
- Evidence: `evidence/PH-01/PH01-ST02/EVD-PH01-ST02-schema-results.json` and `EVD-PH01-ST02-hash-results.json`.

## Safety And Privacy

Source Case forbids runtime credentials and approval state.

## Risks And Follow-up

Renderer and release behavior are handled in later records.
