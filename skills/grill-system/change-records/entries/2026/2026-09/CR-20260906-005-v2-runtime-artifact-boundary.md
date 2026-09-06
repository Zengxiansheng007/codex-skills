# CR-20260906-005 - V2 Runtime And Artifact Boundary

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | grill-system |
| Change Type | added / changed / governance / validation |
| Scope | scripts-and-validation / references-and-assets / safety-and-governance / downstream-and-handoff |
| Source | approved ART-GRILL-PHASE-001; GRILL-ST-001 runtime and artifact-helper repair |
| Baseline | 2026-09-06 candidate-to-baseline comparison: V2 runtime, artifact helper, V2 schema, phase contract, artifact test, and phase test were absent; report template, session contract, and validator changed from baseline |
| Author | Codex and runtime subagent |
| Related Records | CR-20260906-001, CR-20260906-002, CR-20260906-003, CR-20260906-004 |

## Summary

Add the candidate-local V2 Grill ledger runtime and protected-artifact boundary. It distinguishes process-ledger mutation from formal-asset permission, freezes a closure-backed batch plan, verifies actual postconditions, and records no-op separately from updated work.

## Context And Problem

The baseline offered only V1 report validation. It could not model a V2 ledger lifecycle, scope a one-use exception, detect path escape through Windows junctions, bind actual postconditions to an authorized batch, or preserve a truthful no-op result.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| scripts/grill_session_runtime.py | V2 ledger CLI | Add `init`, `propose-question`, `record-answer`, `close`, `pause`, `resume`, `reopen`, `checkpoint`, `reconcile-format-only`, `create-exception`, `consume-exception`, `finish-exception`, `prepare-writeback-plan`, `begin-writeback --plan`, `verify-writeback`, and `render-report`; normalize equivalent absolute and workspace-relative plan targets before coverage verification. |
| scripts/grill_artifact_checks.py | Path and hash boundary | Reject path traversal, symlink/reparse and Windows junction escapes; hash actual targets and validate expected postconditions. |
| scripts/test_grill_phase_contract.py | V2 runtime tests | Cover actual temporary-file updates, no-op receipts, public CLI paths, exceptions, closure, paused recovery, stale decisions, legacy read-only, external drift, and duplicate/equivalent absolute-target handling. |
| scripts/test_grill_artifact_checks.py | Artifact helper tests | Cover paths, semantic-version sibling detection, reparse escape, and actual Windows junction fail-closed behavior where supported. |
| schemas/grill-session-v2.schema.json | V2 ledger contract | Add canonical V2 fields for phase/result, protected/process assets, closure, policy, exceptions, recovery, checkpoints, and receipts. |
| references/grill-session-contract.md | Session contract | Describe V2 authority, V1 legacy-read-only behavior, batch requirements, exception lifecycle, and report projection. |
| references/phase-boundary-contract.md | Runtime boundary | Describe non-overwriting ledger, exception lifecycle, frozen batch, actual hash verification, and no-op result. |
| scripts/validate_grill_report.py | Report validation | Keep report validation attached to the embedded ledger while preventing format success from being treated as write authority. |
| assets/grill-report-template.html | Report projection | Render the session ledger as report data without adding an independent decision state. |

## Decision And Alternatives

The runtime records and checks local workflow evidence rather than installing a global interceptor or merging formal documents. A receipt-only success model was rejected because it could not prove target content. Treating an unchanged target as an update was rejected because it would manufacture versions and false merge claims.

## Impact Analysis

- V2 persists one canonical ledger; V1 remains report-inspectable but `legacy-read-only` for all writing paths.
- Active review permits ledger updates only. Formal assets require a closure-backed, scope-approved plan and actual postcondition verification.
- A verified no-op has `contentChanged=false` and `mergePerformed=false`; an actual update must match every frozen target hash. Equivalent workspace-relative and absolute plan paths are normalized before coverage and duplicate checks.
- Windows junction/reparse handling is fail-closed; semantic classification of observed external drift remains a human decision.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Baseline scope | Candidate-versus-baseline SHA-256 comparison | passed | Exact changed paths are enumerated in Sections Changed. |
| Runtime, artifact, and legacy suites | Root independent final-02 | passed | `development/evidence/root-independent/final-02/summary.json`: 34 named functions (14 legacy, 17 phase, 3 artifact), with the file-symlink host-privilege skip and directory-junction pass recorded. |
| Absolute plan normalization | Root reproducer | passed | `development/evidence/root-extra/absolute-path-plan-fixed.json`: `writeback-complete`, `completed`, verified `updated` receipt for canonical `formal/prd.md`. |
| Independent QA | Run 11 and path scope | passed within stated host limit | `candidate/evidence/codex-independent-qa/run-20260906-11/results.json` records 16 PASS plus one symlink host-capability skip; `candidate/evidence/codex-independent-qa/path-scope-run-20260906-01/results.json` records actual junction denial PASS. |
| Structure/change records | create-skill validator with `--require-change-records` | passed | Four final local validator runs returned exit 0 with P0/P1/P2 all zero. |

## Safety And Privacy

No global Skill, ACL, deployment, network, credential, or formal business asset was changed. The runtime's tests mutate only owned temporary files. It detects observable path/hash drift but cannot prove semantic equivalence or universally prevent external tool writes.

## Risks And Follow-up

- The file-symlink path remains unexecuted because this Windows account lacks the required privilege; the actual directory-junction path passed. No claim is made for global interception or semantic classification of drift.
- Keep CR-20260906-001 as the cross-Skill documentation record; CR-20260906-005 traces implementation and test behavior separately.

Refs: FR-001 to FR-012; AC-001 to AC-012.
