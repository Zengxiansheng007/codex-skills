# Phase 1 Boundary Contract

Use this reference before changing `development-system` routing, execution-loop selection, approval gates, final-state decisions, or any Skill body behavior.

## Purpose

This contract turns the Phase 1 repair decisions into operational rules. It prevents the agent from treating high-impact Skill edits as ordinary direct edits and prevents final completion without evidence.

## Route Boundary Rules

Classify the task before implementation:

| Task signal | Route | Reason |
|---|---|---|
| Requirements, PRD, development plan, test plan, RTM, or acceptance changes | `write-prd` through `development-system` | The requirement anchor or traceability may change. |
| Skill body, reference, script, fixture, validator, route, approval, or final-state behavior changes | `create-skill` through `development-system` | Skill behavior changes must be traceable. |
| External/current source gap or unresolved P0/P1 evidence gap | `research` | Do not convert weak evidence into hard requirements. |
| P0/P1 ambiguity, conflicting decision, irreversible choice, or major phase transition | `grill-system` | User-visible one-question decision gate is required. |
| Claude Code, Midscene, browser, deploy, install, or other live adapter use | gated adapter route | Live execution requires exact-scope approval. |
| Execution feedback, defect report, or agent result review | `handoff-feedback-reviewer` or local gap review | Agent output is evidence, not completion authority. |

## Mandatory Workspace-Copy-First Triggers

Use `workspace-copy-first` before implementation when any trigger is true:

1. `multi-file change`: more than one source, reference, script, fixture, config, or report file may change.
2. `high-risk change`: the change affects safety, permissions, deployment, credentials, external calls, live adapters, validation, or final completion.
3. `global Skill edit`: the target is under a global Codex, WorkBuddy, Claude, or other runtime Skill directory.
4. `single-file behavior change`: one file changes behavior, routing, validation, approvals, adapter execution, final-state classification, test expectations, or downstream handoff semantics.

When in doubt, treat the task as requiring `workspace-copy-first`.

## Direct Edit Exception

Direct editing without a workspace copy is allowed only when all are true:

- the edit is a single file;
- the edit is pure wording, formatting, comment, typo, or non-behavioral documentation cleanup;
- no route, validator, fixture, script, approval gate, adapter, final state, or downstream contract changes;
- the edit remains within the approved workspace;
- the final response states why the direct edit exception was safe.

## Approval Boundary Template

Before live, deploy, install, global write, or external-agent execution, capture:

| Field | Required |
|---|---|
| `approvalType` | `dry-run`, `live-adapter`, `global-deploy`, `install`, `external-write` |
| `targetWorkspace` | Exact local path or repository scope |
| `packetOrPlanRef` | Requirement anchor, handoff packet, or plan path |
| `allowedActions` | What the executor may do |
| `forbiddenActions` | What the executor must not do |
| `timeoutOrBudget` | Runtime and cost boundary |
| `dataBoundary` | What private or production data is excluded |
| `expectedEvidence` | stdout/stderr, manifest, report, validator result, feedback packet |
| `fallbackPolicy` | blocked, dry-run only, Codex local fallback, or re-grill |

Dry-run may preview commands and contracts. Live and deploy require explicit user approval for the exact scope.

## Final State Decision Table

Choose exactly one final state:

| State | Required evidence |
|---|---|
| `running` | The next action is mapped to the active requirement anchor and has no open P0/P1 gate. |
| `waiting-approval` | An approval request exists and no in-scope preauthorization authorizes the action. |
| `repair-needed` | Validation or review found a defect that maps to approved scope and can be fixed locally. |
| `requirements-review` | Requirement drift, conflicting confirmation, new phase, or changed scope is detected. |
| `risk-gate-required` | The next action needs live adapter, deploy, install, external write, global write, sensitive data, or irreversible action approval. |
| `blocked-user-decision` | A material product or scope decision cannot be inferred safely. |
| `blocked-external-dependency` | Environment, account, executable, network, permission, or external system is missing. |
| `loop-limit-reached` | Repeated execution cycles produce no new evidence or no new root cause. |
| `resource-limit-reached` | A configured call, time, token, cost, or other resource budget is exhausted. |
| `completed` | Requirement anchor, changed files, validation evidence, sensitive scan, change records, and completion review agree. |
| `failed` | An unrecoverable in-scope failure is evidenced and no allowed repair transition can continue immediately. |

Cancellation and supersession terminate orchestration as requirement-lifecycle events; they are not governed runtime states. A new state requires requirements review and an updated confirmed baseline.

Completion is forbidden when any P0/P1 drift, missing evidence, invalid feedback, skipped critical validation, unapproved global write, or unmapped action remains.

## Validation Expectations

For changes to this boundary:

- add or update at least one fixture that exercises the changed boundary;
- update validator checks so missing boundary assets fail;
- update change records with the Change ID and validation evidence;
- run `validate_development_system.py`;
- run package-level validation when the system package is in scope.
