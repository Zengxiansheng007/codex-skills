# Grill Session Contract

## Active V2 contract

All new persisted Grill sessions use [grill-session-v2.schema.json](../schemas/grill-session-v2.schema.json) and `scripts/grill_session_runtime.py`. This single canonical ledger is the only report decision source. V1 is legacy-read-only and cannot authorize closure, a mid-review exception, or document writeback.

```json
{
  "schemaVersion": "2.0",
  "sessionId": "grill-YYYYMMDD-HHMM",
  "scenario": "requirements",
  "ledgerPath": ".grill/session.json",
  "workspaceRoot": ".",
  "phase": "grilling",
  "result": "in-progress",
  "recordMode": "ledger",
  "questions": [], "decisions": [], "effectiveDecisions": [], "evidenceIndex": [], "openItems": [], "nextActions": [],
  "sourceBaseline": [], "protectedAssets": [], "processArtifacts": [{"kind": "ledger", "path": ".grill/session.json"}],
  "closureEvidence": {}, "writebackPolicy": {"mode": "default-batch", "approvedScopes": []},
  "exceptions": [], "recovery": {"lastSafePhase": "grilling", "nextQuestionId": null}, "checkpoints": [], "writebackReceipts": []
}
```

Use `render-report` only after closure. It embeds the exact ledger in the `grill-session` JSON block and renders phase/result/decisions from that object; it never stores a separate report decision state. `conversation-only` returns an in-memory projection and writes no ledger or report file.

## Legacy V1 read-only compatibility

The following V1 shape remains supported only for report inspection. It validates against [grill-session.schema.json](../schemas/grill-session.schema.json) (Draft 2020-12), but its historical `status` cannot be used as V2 closure or writeback authority. Failure classes are defined in [schemas/grill-failure-classification.json](../schemas/grill-failure-classification.json).

```json
{
  "sessionId": "grill-YYYYMMDD-HHMM",
  "scenario": "test-case-design",
  "status": "complete",
  "sourceInputs": [
    {"type": "prd", "pathOrLabel": "requirements.md", "freshness": "unknown"}
  ],
  "questions": [
    {
      "id": "Q-001",
      "question": "Which source should be treated as authoritative for current behavior?",
      "purpose": "Decide whether test cases should follow PRD, UI, code, or production behavior.",
      "evidence": ["E-001"],
      "recommendedAnswer": "Use running product behavior as current truth and mark PRD/Figma drift as requirement risk.",
      "blockingDecision": "test oracle source",
      "userResponse": "confirmed",
      "status": "confirmed",
      "severity": "P0"
    }
  ],
  "decisions": [
    {
      "id": "D-001",
      "title": "Use running product as the test oracle",
      "sourceQuestion": "Q-001",
      "decision": "confirmed",
      "consequence": "Generated cases must cite product evidence when PRD conflicts."
    }
  ],
  "evidenceIndex": [
    {"id": "E-001", "type": "code", "pathOrUrl": "src/module", "claim": "module is still routed"}
  ],
  "openItems": [
    {"id": "O-001", "severity": "P2", "owner": "product", "question": "Confirm final copy for empty state."}
  ],
  "nextActions": [
    {"type": "skill", "target": "to-spec", "reason": "Requirement decisions are ready for spec synthesis."}
  ]
}
```

## Status Values

- `draft`: grilling started but is not ready to use.
- `blocked`: a required decision or evidence source is unavailable.
- `complete`: P0 open items are zero and next action is clear.
- `risk-accepted`: P0 open items remain, but the user explicitly accepted the risk.

## Question Status Values

- `proposed`: agent asked and is waiting.
- `confirmed`: user accepted the answer.
- `changed`: user supplied a different answer.
- `rejected`: user rejected the premise.
- `needs-evidence`: fact lookup or research is required.

## Severity

- `P0`: blocks safe execution or materially changes scope.
- `P1`: likely changes design, coverage, or validation.
- `P2`: improves completeness or maintainability.

## V2 phase-boundary ledger

New write-capable sessions use [grill-session-v2.schema.json](../schemas/grill-session-v2.schema.json). The legacy V1 shape above remains valid only for report inspection: it is `legacy-read-only` and never supplies closure or writeback authority.

V2 keeps `phase` separate from `result`. `phase` records `grilling`, `awaiting-closure`, `review-ended`, `writeback`, `writeback-complete`, `paused`, `repair-needed`, or `blocked`; `result` records whether the session is in progress, ready for a default batch, conclusions-only, completed, partial-failure, blocked, or repair-needed. A question answer never supplies `closureEvidence`; only an explicit session-close record with a user-backed statement, source, and timestamp can move to `review-ended`.

`questions`, `decisions`, `effectiveDecisions`, `openItems`, and `evidenceIndex` are one canonical ledger. A reopened question appends `reopenHistory` with its reason and new evidence, and supersedes rather than deletes its prior effective decision. Every unresolved P0 question must appear in `openItems` through `sourceQuestion`; every P0 open item needs the same link. A risk acceptance must name the `openItemId`, concrete risk, acceptance basis, affected scope, and accepting authority.

`writebackPolicy.mode` defaults to `default-batch`; `conclusions-only` and `deferred` produce no formal-document merge. A V2 batch requires explicit closure, `review-ended`, a checkpoint of normalized protected assets, and approved scopes. The runtime records evidence and checks actual postcondition hashes after a downstream document Skill performs a merge. It does not merge formal content itself. A receipt is incomplete until it covers every observed protected-scope change and each actual file hash matches its expected postcondition. Repeating an already verified receipt is a no-op; a partial result is `repair-needed` and retains per-item progress for recovery.

`protectedAssets` is a list of `{path, kind}` entries where `kind` is `file` or `directory`. Paths are resolved inside the explicit `workspaceRoot`; parent traversal, outside-root paths, and reparse/symlink entries fail closed. A protected file also observes same-directory version replacements such as `name-v2.md` and `name-v2.1.md`. The checker records content drift only; it does not infer whether drift is semantic. A human must classify drift before affected work can continue.

An exception is a one-use, bounded object with an authorization, explicit scope, and `preCheckpointId`. Its `status` becomes `consumed` or `expired` after use; later questions do not inherit the exception. `ledgerPath` is immutable for V2 mutations and is listed in `processArtifacts`; neither it nor another process artifact may overlap a protected asset.
