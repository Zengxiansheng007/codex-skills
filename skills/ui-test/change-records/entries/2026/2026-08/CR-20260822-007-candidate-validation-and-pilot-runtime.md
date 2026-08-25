# CR-20260822-007 - Candidate Validation And Pilot Runtime

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | ui-test |
| Change Type | fixed / validation / governance |
| Scope | core-skill-md / scripts-and-validation / safety-and-governance |
| Source | PH-05 implementation gap and final candidate validation |
| Baseline | workspace candidate after PH-04; 88 tests passed |
| Author | Codex |
| Related Records | CR-20260822-006 |

## Summary

Connected a current-run redacted Approval Record and one-shot R2 guard to the D-drive private pilot, added exact test-host matching and canonical zero-submit failure results, and aligned the candidate with the current Skill quality validator.

## Context And Problem

The core guard existed, but the generated pytest pilot still relied on an environment switch and local submit counter. Candidate documentation also predated the current Validation, Safety and change-record contracts.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `pilot/build_tianjin_pilot.py` | generated runtime | Add approval, host, one-shot submit and RunResult governance |
| `pilot/run_private_pilot.py` | child process | Pass explicit current-run approval and in-memory host value |
| `SKILL.md` | Escalation | Add explicit approval and refusal boundaries |
| `change-records/` | traceability | Bring index, ledgers and records to the current contract |
| `ui-test-checkpoint-runtime/playwright_runner.cjs` | route assertion | Match public host in memory and persist only match status |

## Decision And Alternatives

Use a deterministic local guard before the visible UI click. Do not persist an approval in Source Case, reuse an approval across runs, or rely on an environment variable alone.

## Detailed Change

Each run creates a redacted Approval Record bound to `run_id`, `case_id`, test environment, visible UI, the create action and one submit. Failure before submit produces a canonical RunResult with `submit_count=0`.

## Impact Analysis

Manual pytest execution now fails closed without `--ui-r2-approved`. Network failure, locator failure and post-submit uncertainty remain distinguishable and cannot trigger a second create.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Runtime templates | Python unit tests | passed, 3 tests | local test output |
| Candidate suite | pytest | passed, 99 tests | local test output |
| Pilot collection | pytest collect-only | passed, 2 tests without unknown-marker warnings | PH-03 collection evidence |
| Private connectivity | redacted TCP probe | blocked at TCP timeout | PH-05 connectivity evidence |

## Safety And Privacy

Credentials and the exact endpoint remain child-process memory only. No private page is sent to Midscene or Claude. No API create, production action, cleanup or second submit is permitted.

## Risks And Follow-up

P0-A and P0-B live completion is blocked until the private test endpoint becomes reachable. Global installation remains separately approval-gated.

Refs: PH05-ST04, AC-CASE-044
