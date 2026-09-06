# Shared Artifact Contracts

This file is the shared contract for `write-prd`, `write-requirements-prd`, `architecture-design`, `development-plan`, and `test-plan`.

## Artifact Envelope

Every governed artifact must include an envelope:

```yaml
artifact:
  id: ART-000
  type: prd | architecture | development-plan | test-plan | review | impact-analysis
  title: ""
  version: "v0.1"
  statusCode: draft
  statusLabelZh: 草稿
  createdAt: YYYY-MM-DD
  updatedAt: YYYY-MM-DD
  owner: user
  sourceBaseline:
    sources: []
    capturedAt: YYYY-MM-DD
    fingerprint: ""
  upstreamArtifacts: []
  downstreamArtifacts: []
  riskAccepted: []
  openQuestions: []
  rtmRef: ""
```

## Status Mapping

| statusCode | statusLabelZh | Meaning |
| --- | --- | --- |
| `draft` | 草稿 | Work is not ready for review or downstream use. |
| `grilling` | 消歧中 | Material questions are being resolved through `grill-system`. |
| `review` | 待评审 | Content is complete enough for review, but not approved. |
| `approved` | 已批准 | P0 is closed, quality gates passed, and the artifact can be consumed. |
| `risk-accepted` | 风险接受 | Residual risk is explicitly accepted and must propagate downstream. |
| `stale` | 已过期 | Upstream baseline changed or evidence freshness is invalid. |
| `reopened` | 已重开 | A prior approval was reopened by semantic change or defect. |
| `superseded` | 已替代 | A newer artifact version replaces this one. |
| `partial` | 部分完成 | Output is useful but cannot satisfy full readiness. |
| `blocked-user-decision` | 等待用户决策 | A material decision cannot be inferred safely. |
| `repair-needed` | 需要修复 | Validation or review found an in-scope defect. |

Do not expose a bare English status to the user without the Chinese label.

## Stable IDs

Use these identifiers consistently:

| Item | Pattern |
| --- | --- |
| Goal | `GOAL-nnn` |
| Functional requirement | `FR-nnn` |
| Business rule | `BR-nnn` |
| Non-functional requirement | `NFR-nnn` |
| Acceptance criterion | `AC-nnn` |
| Open question | `OQ-nnn` |
| Risk | `RISK-nnn` |
| Architecture element | `ARC-nnn` |
| Architecture decision | `ADR-nnn` |
| Development task | `TASK-nnn` |
| Test area | `TA-nnn` |
| Test coverage item | `TCOV-nnn` |
| Evidence item | `EVD-nnn` |
| Change impact item | `CHG-nnn` |

IDs are stable after publication. Do not renumber existing IDs during edits; mark removed items as superseded.

## RTM Minimum Columns

The RTM must support these columns when applicable:

| Column | Required for |
| --- | --- |
| Goal ID | PRD and downstream artifacts |
| FR/BR/NFR ID | PRD and downstream artifacts |
| AC ID | PRD and downstream artifacts |
| Architecture mechanism / ADR | Architecture and later |
| Development task | Development and later |
| Test coverage item | Test plan and later |
| Evidence item | Test plan and execution handoff |
| Status code / Chinese label | All governed artifacts |
| Risk / open question | All impacted artifacts |

P0/P1 FR and NFR rows must map to at least one acceptance criterion, one downstream implementation or architecture mechanism when in scope, one test coverage item when in scope, and evidence expectations.

## Source Baseline

Every artifact must record:

- source paths, URLs, pasted notes, or prior artifact IDs used;
- capture date;
- version, commit, timestamp, or checksum when available;
- known stale sources;
- facts versus assumptions.

Unknown business facts must stay as assumptions or open questions. Do not invent URLs, accounts, owners, thresholds, fields, endpoints, compliance claims, or environment capabilities.

## Change Impact And Reopen

Treat these as semantic changes:

- goal or success metric changes;
- scope or non-goal changes;
- role, permission, or terminology meaning changes;
- business rule changes;
- state transition or data lifecycle changes;
- interface behavior changes;
- NFR, AC, evidence, release, rollback, or risk acceptance changes.

For semantic changes, create an impact record with changed IDs, affected artifacts, required revalidation, owner, and target state. Mark downstream artifacts `stale` or `reopened` before using them.

Pure formatting, typo, link, or display-only numbering edits do not require reopen unless they change meaning.

## Grill Phase Boundary

When an artifact is under an active Grill review, its formal body and all formal metadata are frozen, including version, status, dates, RTM, and substitute versions. The Grill ledger is the sole per-answer update target. Whole-review closure is distinct from a confirmed question, an artifact approval, an implementation result, and a rendered report.

On a closure-backed `review-ended` / `ready-for-writeback` result, reuse the established authorization for one centralized batch update; do not ask it again. A notes-only policy has zero formal writes. Preserve any external edit observed during the fresh-baseline check. If it changes a reviewed meaning, reopen only the linked decisions and retain the affected artifact history. `paused`, `blocked`, `repair-needed`, `partial-failure`, and `legacy-read-only` are non-writing results. The boundary is workflow and evidence governance, not a claim of OS-level interception.

Before a batch, freeze effective decision content, approved scopes, and planned `{id, path, expectedSha256}` postconditions. A receipt with outcome `no-op` means every planned postcondition already matched: it must not create a new version or change body, metadata, status, dates, or RTM. A receipt with outcome `updated` requires each actual target hash to match its frozen postcondition. Record incomplete or mismatched work as partial failure or repair-needed; never infer success from a command exit code or a report.

## Risk Acceptance

Risk acceptance requires:

- risk ID and description;
- impacted GOAL/FR/NFR/AC IDs;
- accepting authority;
- date;
- expiry or review condition;
- downstream propagation requirement;
- validation duties that still remain.

`risk-accepted` is not equivalent to published, deployed, or tested.
