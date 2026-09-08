# Feedback Review Rules

Reject free-form completion summaries. Require structured feedback, evidenceIndex, requirementTraceDelta, and driftReview.

Any untracedAction blocks completion.

## Research Failure Class Review (FR-RR-006)

When reviewing research feedback, map the stable failure classes from the research-guided skill's `schemas/failure-classification.json` to drift severity:

| Research Failure Class | Drift Severity | Reviewer Action |
|---|---|---|
| `plan-mode-blocked` | P0 | Reject; route to repair |
| `unregistered-tool-requested` | P0 | Reject; route to user decision |
| `mcp-schema-absent` | P0 | Reject; route to external dependency |
| `tool-count-zero` | P0 | Reject; route to external dependency |
| `stale-session` | P0 | Reject; route to repair |
| `canary-missing` | P0 | Reject; route to repair |
| `canary-failed` | P0 | Reject; route to repair |
| `permission-denials-nonzero` | P0 | Reject; route to user decision |
| `output-not-json` | P0 | Reject; route to repair |
| `source-mappings-invalid` | P0 | Reject; route to repair |
| `unverified-sources-claimed-complete` | P0 | Reject; route to repair |
| `format-retry-limit-exceeded` | P1 | Reject; route to repair |
| `reinforcement-limit-exceeded` | P1 | Reject; route to repair |
| `claude-unavailable` | P1 | Reject; route to external dependency |
| `timeout` | P1 | Reject; route to external dependency |
| `internal-error` | P1 | Reject; route to repair |

Never accept a research result that contains a failureClass. Never mark research completed when P0/P1 failure classes are present.

## Adapter-Validated Failure Class Review (FR-ADP-008)

When reviewing adapter-validated Research feedback, map the two-stage adapter
failure classes to drift severity. Compatibility mode must be explicit; a silent
downgrade is always rejected.

| Adapter Failure Class | Drift Severity | Reviewer Action |
|---|---|---|
| `structured-output-empty` | P0 | Reject; route to external dependency; select adapter-validated profile explicitly |
| `silent-native-downgrade` | P0 | Reject; route to repair; mode must be explicit |
| `evidence-ledger-missing` | P0 | Reject; route to repair; freeze a ledger before serialization |
| `evidence-hash-unstable` | P0 | Reject; route to repair; use one unchanged evidence hash |
| `unsupported-fact-introduced` | P0 | Reject; route to repair; serialize only from the frozen ledger |
| `serialization-tool-access` | P0 | Reject; route to repair; serialization must expose no tools |
| `adapter-validation-failed` | P0 | Reject; route to repair; local Schema/semantic gates must pass |
| `format-attempt-exhaustion` | P1 | Reject; route to repair; mark blocked or repair-needed |

A research result that records `schemaEnforcementMode=adapter-validated` must
also record `providerNativeSchema=false` and a non-empty `evidenceLedgerRef`.
A result that records `schemaEnforcementMode=provider-native` with
`providerNativeSchema=false` is a silent downgrade and must be rejected.

## Router Feedback Boundary

The tables above classify preserved guided Claude packets. The research router also emits paused and pending-guided states; neither is a completed research result. Require actual matching executor/task/generation evidence, source/claim mappings, full objective coverage and Codex review before completion. Unknown AnySearch errors pause immediately; no implicit retry, Codex bypass or automatic recovery is allowed. Do not demand fabricated Claude-specific fields from explicit Codex or AnySearch profiles.
