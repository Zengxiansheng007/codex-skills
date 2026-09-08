# CR-20260816-004 - PH-4 Installation And Operations Governance

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | development-system |
| Change Type | added / validation / governance |
| Scope | scripts / schemas / references / fixtures / change records |
| Source | DSCR-PH-4; DSCR-ST-4-001 through DSCR-ST-4-003 |
| Author | Codex bounded takeover after Claude timeout; Codex owns completion |

## Summary

Add a deterministic PH-4 module for compatibility assessment, backup manifest construction, exact user installation approval and operations/audit governance. Actual user-level installation is intentionally not performed and remains a separate user approval gate.

## Context And Problem

The final requirement needs promotion and operations governance, but workspace validation alone cannot authorize a user-level Skill overwrite. Before this change, the boundary existed in prose but did not have a deterministic approval object, backup manifest contract, negative matrix or reconstructible operations report.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `SKILL.md` | References, validation, DSCR-PH-4 capability | Route promotion work through the exact approval contract. |
| `references/phase4-install-operations-contract.md` | New | Define compatibility, rollback, approval and operations rules. |
| `scripts/phase4_governance.py` | New | Implement deterministic PH-4 gates. |
| `scripts/test_phase4_governance.py` | New | Test positive readiness and four fail-closed boundaries. |
| `schemas/*.schema.json` | PH-4 schemas | Define approval, backup and operations shapes. |
| `assets/fixtures` | PH-4 fixtures | Add positive promotion/operations and negative approval cases. |
| `scripts/validate_development_system.py` | Required files | Fail when any PH-4 asset is missing. |

## Decision And Alternatives

Selected a separate pure deterministic module that reuses existing hashing, status and audit concepts without expanding the public handoff schema. Rejected performing a real install during development, treating workspace validation as approval, or embedding install logic inside Claude prompts.

## Changes

- `phase4_governance.py`: compatibility, backup, install approval and operations report functions.
- `test_phase4_governance.py`: positive dry-run readiness plus missing approval, source drift, missing rollback and expired approval failures.
- Three schemas and six fixtures for PH-4 contracts.
- Validator and `SKILL.md` now require and route through the PH-4 contract.

## Requirement Trace

| Story | Evidence |
|---|---|
| DSCR-ST-4-001 | compatibility assessment, backup manifest, rollback-required negative fixture |
| DSCR-ST-4-002 | exact install gate, missing/expired/mismatched approval fixtures |
| DSCR-ST-4-003 | reconstructible operations report, resource/failure budget and Chinese status fixture |

## Impact Analysis

- Adds only workspace candidate files and additive Skill references.
- Strengthens the protected installation boundary; existing direct-development behavior is unchanged.
- Introduces no third-party dependency and no network requirement.
- Downstream installers must supply an exact approval and backup evidence before any write.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| PH-4 contract test | `python scripts/test_phase4_governance.py` | pass | `PH4_GOVERNANCE_OK` |
| Development runtime | `python scripts/test_development_runtime.py` | pass | `DEVELOPMENT_RUNTIME_OK` |
| Skill validator | `python scripts/validate_development_system.py` | pass | P0/P1/P2 = 0/0/0 |
| Claude live | HCE manifest | blocked | timeout after 600 seconds; no valid feedback |

## Safety And Privacy

No user-level installation, global write, production action, dependency installation, network access or credential read occurred. Approval fixtures contain placeholders only. Claude execution was bounded to the approved workspace and its timeout was preserved as blocked evidence.

## Risks And Follow-up

The PH-4 capability is testable and installation-ready, but DSCR-ST-4-002 and the PH-4 exit gate remain open until the user separately approves the exact source hash, target path and overwrite coverage, after which backup, install, restore evidence and post-install smoke must be executed.

## Boundaries And Rollback

No global Skill write or user-level installation occurred. Rollback removes the PH-4 module, test, schemas, reference, fixtures and this record, then removes their validator and `SKILL.md` references.
