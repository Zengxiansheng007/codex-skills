# Core Skill MD Change Ledger

## Purpose

Track normative routing, workflow, validation and escalation changes in `SKILL.md`.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-09-04 | CR-20260904-002 | Project Asset Governance, Validation and Escalation | changed | Require 2.2/V3/AttemptV2/V5 transactional close-out and external process acceptance | applied |
| 2026-09-04 | CR-20260904-001 | Execution Context Governance | changed | Require root pytest plugin, v2.1 execution, origin/approval separation and manual A/B completion gate | applied |
| 2026-09-03 | CR-20260903-001 | Project Asset Governance | changed | Require registry-backed module postconditions, recursive product hierarchy and two-phase activation | validated |
| 2026-09-02 | CR-20260902-001 | Project Asset Governance and validation | changed | Route editable branch data through test-data v2 and require v2 compile/sync/execution gates | validated |
| 2026-08-18 | CR-20260818-001 | Unified Packet Contract | changed | Document validator entrypoint and fail-closed boundary | applied |
| 2026-08-22 | CR-20260822-007 | Escalation | added | Add explicit private-page, R2, installation and production gates | validated |

## Detailed Records

### CR-20260904-002 - pycharm-finalization-transaction-v2

- Section changed: formal execution, completion validation and migration boundary.
- Before: V2/V1/V4 allowed terminal-before-finalizer behavior and RunResult self-attested PyCharm/human status.
- After: 2.2/V3/AttemptV2/V5 requires commit plus receipt before terminal, SessionResult and external AcceptanceResult.
- Why: prevent terminal, result and real helper exit from splitting.
- Impact: old 2.1/V2/V1/V4 is audit-only; no installation or R2 authority is granted.
- Validation: focused runtime/contracts passed; full candidate and helper canary remain pending.
- Detail record: `../entries/2026/2026-09/CR-20260904-002-pycharm-finalization-transaction-v2.md`.

### CR-20260822-007 - candidate-validation-and-pilot-runtime

- Section changed: Validation and Escalation.
- Before: no validator-recognized escalation section.
- After: explicit approval and refusal conditions.
- Why: candidate quality gate required a visible safety boundary.
- Impact: no new execution authority.
- Validation: create-skill validator and package tests.
- Detail record: `../entries/2026/2026-08/CR-20260822-007-candidate-validation-and-pilot-runtime.md`.
