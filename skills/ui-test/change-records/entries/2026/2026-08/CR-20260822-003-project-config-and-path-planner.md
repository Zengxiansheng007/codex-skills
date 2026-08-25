# CR-20260822-003 - Project Config And Path Planner

| Field | Value |
|---|---|
| Status | applied |
| Target Skill | ui-test |
| Story | PH01-ST03 |
| Requirements | FR-CASE-012, FR-CASE-018, FR-CASE-023, FR-CASE-028, FR-CASE-029, FR-CASE-051..056 |
| Acceptance | AC-CASE-010, AC-CASE-015, AC-CASE-027, AC-CASE-028, AC-CASE-030, AC-CASE-042 |

## Summary

Add the write-capable `ui-test.project.v2` contract, retain v1 only for read-only inventory, and add a governed Path Planner. The planner maps each registered UI-Test asset type to its only permitted root, resolves the configured business scope, uses stable ID plus display-name segments, and rejects caller-selected output roots, unknown scope, lexical escape, symlink and junction paths.

## Context And Problem

UI-Test assets were scattered and callers could choose arbitrary roots.

## Sections Changed

Project config schema/loader, Path Planner and path tests.

## Decision And Alternatives

Use type-to-root mapping and stable business hierarchy rather than convention-only paths.

## Impact Analysis

Formal UI-Test assets are confined to governed D-drive roots.

## Boundary

The double-root rule applies only to registered UI-Test project assets. Ordinary workspace documents, other Skill assets and global Skill programs remain outside Path Planner enforcement. This Story plans paths but does not create formal D-drive project assets.

## Validation Evidence

- Full candidate `ui-test` suite: 60 tests passed, 0 skipped.
- A real Windows junction under a disposable workspace fixture returned `E_PATH_REPARSE_POINT_BLOCKED`.
- v1 write, C-drive caller root, root-type mismatch, unknown asset type, unknown module and lexical escape negative cases all fail closed.
- Evidence: `evidence/PH-01/PH01-ST03/EVD-PH01-ST03-path-matrix.json` and `EVD-PH01-ST03-project-config.json`.

## Safety And Privacy

Project config stores environment-key names, not values.

## Risks And Follow-up

Existing assets require dry-run inventory before disposition.
