# Downstream And Handoff

## Purpose

Define how research results, failure classes, and evidence propagate to downstream skills: handoff-claude-executor, handoff-feedback-reviewer, and development-system.

## Research Result Propagation

Research results validated by `schemas/research-result.schema.json` and `scripts/validate_research_result.py` are the authoritative output of the research skill. Downstream skills must not accept unvalidated research output.

## Failure Class Propagation (FR-RR-006)

Stable failure classes defined in `schemas/failure-classification.json` propagate as follows:

| Failure Class | Research Action | Handoff Executor Action | Feedback Reviewer Action | Development System Action |
|---|---|---|---|---|
| `plan-mode-blocked` | Block live research | Classify as `repair-needed` | Reject completion | Route to repair |
| `unregistered-tool-requested` | Block and record | Classify as `blocked-user-decision` | Reject completion | Route to user decision |
| `mcp-schema-absent` | Block and record | Classify as `blocked-external-dependency` | Reject completion | Route to external dependency |
| `tool-count-zero` | Block and record | Classify as `blocked-external-dependency` | Reject completion | Route to external dependency |
| `stale-session` | Block and record | Classify as `repair-needed` | Reject completion | Route to repair |
| `canary-missing` | Block and record | Classify as `repair-needed` | Reject completion | Route to repair |
| `canary-failed` | Block and record | Classify as `repair-needed` | Reject completion | Route to repair |
| `permission-denials-nonzero` | Block and record | Classify as `blocked-user-decision` | Reject completion | Route to user decision |
| `output-not-json` | Block and record | Classify as `repair-needed` | Reject completion | Route to repair |
| `source-mappings-invalid` | Block and record | Classify as `repair-needed` | Reject completion | Route to repair |
| `unverified-sources-claimed-complete` | Block and record | Classify as `repair-needed` | Reject completion | Route to repair |
| `format-retry-limit-exceeded` | Flag P1 and record | Classify as `repair-needed` | Reject completion | Route to repair |
| `reinforcement-limit-exceeded` | Flag P1 and record | Classify as `repair-needed` | Reject completion | Route to repair |
| `claude-unavailable` | Block and record | Classify as `blocked-external-dependency` | Reject completion | Route to external dependency |
| `timeout` | Block and record | Classify as `blocked-external-dependency` | Reject completion | Route to external dependency |
| `internal-error` | Block and record | Classify as `repair-needed` | Reject completion | Route to repair |

## Adapter-Validated Failure Class Propagation (FR-ADP-008)

The two-stage adapter-validated compatibility profile adds failure classes
that propagate through the same downstream skills. They are stable identifiers
and must never map a result to `completed`.

| Failure Class | Research Action | Handoff Executor Action | Feedback Reviewer Action | Development System Action |
|---|---|---|---|---|
| `structured-output-empty` | Select adapter-validated profile explicitly | Classify as `blocked-external-dependency` | Reject completion | Route to external dependency |
| `silent-native-downgrade` | Reject; mode must be explicit | Classify as `repair-needed` | Reject completion | Route to repair |
| `evidence-ledger-missing` | Freeze a ledger before serialization | Classify as `repair-needed` | Reject completion | Route to repair |
| `evidence-hash-unstable` | Re-freeze one ledger | Classify as `repair-needed` | Reject completion | Route to repair |
| `unsupported-fact-introduced` | Reject; serialize only from the ledger | Classify as `repair-needed` | Reject completion | Route to repair |
| `serialization-tool-access` | Remove serialization tools | Classify as `repair-needed` | Reject completion | Route to repair |
| `adapter-validation-failed` | Fix Schema/semantic gates | Classify as `repair-needed` | Reject completion | Route to repair |
| `format-attempt-exhaustion` | Mark blocked or repair-needed | Classify as `repair-needed` | Reject completion | Route to repair |

## No Silent Downgrade (FR-ADP-001, FR-ADP-007)

Compatibility mode (`adapter-validated`) is selected only by an explicit
profile. A provider-native failure must never silently activate
adapter-validated mode; the run must record `schemaEnforcementMode` and
`providerNativeSchema` honestly. Provider-native behavior remains available and
unchanged for capable gateways.

## Handoff Executor Contract

The handoff-claude-executor must:
1. Run preflight checks before live research (FR-RR-003).
2. Reject permission mode plan before spawning Claude (FR-RR-001).
3. Validate research output against `research-result.schema.json` (FR-RR-004).
4. Propagate failure classes from `failure-classification.json` (FR-RR-006).
5. Enforce format retry and reinforcement bounds (FR-RR-005).

## Feedback Reviewer Contract

The handoff-feedback-reviewer must:
1. Reject any research result that does not pass schema and semantic validation.
2. Map failure classes to drift severity levels.
3. Never accept unverified sources as complete evidence.

## Development System Contract

The development-system must:
1. Route research failure classes to the appropriate next state.
2. Never mark research as completed when P0/P1 failure classes are present.
3. Preserve failure class names as stable identifiers across all contracts.
