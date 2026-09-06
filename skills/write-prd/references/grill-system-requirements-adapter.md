# Grill System Requirements Adapter

This adapter describes how `write-requirements-prd` must use the existing `grill-system` requirements branch.

## Entry Conditions

Enter `grill-system` when:

- creating a new PRD;
- making a major semantic PRD change;
- P0/P1 ambiguity exists;
- preparing a PRD for approval;
- a user asks to skip clarification and the skip would affect P0/P1 certainty.

Pure formatting edits and read-only reviews can skip grill unless P0/P1 ambiguity is discovered.

## Phase Boundary

This adapter inherits Grill's review boundary for the requirements route. During active review, update one authoritative structured ledger per answer and freeze every formal artifact: body, metadata, version, status, timestamp, RTM, and substitute versions. Do not use a report, a question confirmation, a callee return, or a legacy report as write authorization.

The exact candidate schema is the source of field-level validation. The semantic contract below names the stable responsibilities so this adapter does not turn an implementation detail into a conflicting second authority.

## Call Contract

The caller must pass:

```yaml
grillRequest:
  sessionId: GRILL-YYYYMMDD-nnn
  branch: requirements
  sourceArtifactId: ART-000
  sourceBaseline: {}
  questionMode: one-at-a-time | numbered-batch
  allowedBatch: false
  blockingCategories:
    - goals
    - scope
    - roles
    - business-rules
    - state
    - data
    - interface
    - nfr
    - acceptance
    - evidence
  returnTo: write-requirements-prd
  phaseBoundary:
    protectedAssets: [formal-prd, formal-rtm, formal-metadata, substitute-versions]
    defaultWriteback: centralized-batch-after-explicit-closure
    notesOnly: false
```

## Return Contract

`grill-system` must return:

```yaml
grillResult:
  sessionId: GRILL-YYYYMMDD-nnn
  phase: grilling | awaiting-closure | review-ended | writeback | writeback-complete | paused | blocked | repair-needed
  result: ready-for-writeback | conclusions-only | completed | partial-failure | blocked | repair-needed | legacy-read-only
  questions: []
  decisions: []
  effectiveDecisions: []
  openItems: []
  closureEvidence: {}
  writebackPolicy: {}
  protectedAssets: []
  processArtifacts: []
  exceptions: []
  recovery: {}
  checkpoints: []
  writebackReceipts: []
  evidenceIndex: []
  reportRef: "" # Projection only; not closure or write authorization.
```

`write-requirements-prd` may write only when `phase` is `review-ended`, `result` is `ready-for-writeback`, `closureEvidence` is present, and `writebackPolicy` is not notes-only. It freezes effective decision content, approved scopes, and a planned `{id, path, expectedSha256}` set before the authorized centralized batch, then records `writebackReceipts`.

Use the public `prepare-writeback-plan` command to produce the plan's decision and scope fingerprints; do not calculate or copy a private runtime fingerprint algorithm. Register the generated plan in `processArtifacts` as a `writeback-plan` before `begin-writeback --plan` consumes it.

If all planned postconditions already match, the receipt outcome is `no-op`: do not claim a merge or change PRD body, metadata, version, status, date, or RTM. If a target changes, the receipt outcome is `updated` only after every actual target hash matches its frozen expected hash. `conclusions-only`, `paused`, `blocked`, `repair-needed`, `partial-failure`, and `legacy-read-only` preserve the ledger without a PRD write. A semantic conflict preserves external edits and reopens only affected questions. Do not recursively re-enter the same Grill session unless new material evidence requires it.

## Question Rules

- Default to one highest-value decision question per message.
- If the user explicitly allows batch mode, one message may contain multiple numbered questions.
- Each batch question must have independent purpose, evidence, recommended answer, blocking decision, and status.
- The user must answer each numbered question; a global confirmation cannot close unanswered questions.
- Facts must be looked up in available sources before asking the user.
