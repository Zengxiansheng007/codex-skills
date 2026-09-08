---
name: development-system
description: >-
  Reusable Codex development hub and top-level router. Use when Codex must turn a user goal into a requirement anchor, research-backed PRD, development plan, test plan, landed implementation review, RAG writeback, publish manifest, A2A handoff packet, Claude/Midscene execution review loop, or gap-to-requirement decision cycle.
---

# Development System

## Positioning

`development-system` is the reusable Codex development hub, also called **Development System**.

Use this skill as the first entry point when the task is bigger than direct execution and needs requirement anchoring, evidence review, PRD or plan generation, A2A handoff, feedback review, or multi-round adjustment. It routes to downstream skills; it does not replace them.

## Non-negotiable Rules

- Codex is the sole control plane and completion authority. Only Codex may approve state transitions, Agent invocations, risk gates, rework routing and `completed` writes.
- Execution Agents such as Claude Code or Midscene are downstream executors or observers. Independent Skills keep their own ownership and participate only through versioned interfaces.
- Use Claude-first for multi-file changes, Skill development, complex repairs and cross-module work. A Codex-local exception must be one of `documentation-only`, `single-file-non-behavior` or `simple-local-task`.
- Codex may self-approve live Agent calls and bounded takeover only when workspace, actions, data, network, tools and timeout all match an active user preauthorization. Any mismatch fails closed.
- User-level Skill installation, production writes, publishing, external messages, credential export and unrelated global changes always require a new explicit user approval.
- Do not continue a loop when feedback has P0/P1 requirement drift, missing evidence, invalid schema, or unmapped actions.
- If a user confirmation conflicts with a grill decision record, confirmed requirement, or active requirement anchor, route to requirements review before execution.
- Use `workspace-copy-first` before implementation for any multi-file change, high-risk change, global Skill edit, or single-file behavior change. Direct edits are limited to pure wording, formatting, comments, or other non-behavioral documentation changes.
- A stop signal, timeout, circuit state, resource limit or Agent claim is never a completion signal. `completed` requires the Codex CompletionEvaluator.

## Router Workflow

1. **Frame the task.** State the interpreted goal, target artifact, scope, non-goals, risk level, and whether the task requires detailed understanding.
2. **Create or update the requirement anchor.** Capture original goal, approved scope, non-goals, FR/AC mapping, authority order, source baseline, manual confirmation actions, and current iteration objective.
3. **Run evidence gate when needed.** Route to `research` when the task depends on current external facts, unfamiliar products, third-party tools, security, runtime adapters, standards, or unresolved P0/P1 evidence gaps.
4. **Run grill gate when needed.** Route to `grill-system` for P0/P1 ambiguities, conflicting goals, high-risk choices, irreversible actions, or major phase transitions.
5. **Create governed artifacts.** Route to `write-prd` for PRD, architecture, development plan, test plan, RTM and DoR/DoD. `write-prd` delegates to `write-requirements-prd`, `architecture-design`, `development-plan`, and `test-plan`. Wrap every governed artifact in a stable envelope.
6. **Decompose into Phase and Story.** Every complex task needs Phase entry/exit criteria and small, testable Stories mapped to FR/AC, dependencies and evidence.
7. **Assign private profiles.** Use Product/Requirement, Architect, Project Planner, Engineer and QA responsibilities as internal Profiles; Codex controls stage entry and exit.
8. **Apply workspace and approval gates.** Use workspace-copy-first, then require a complete preauthorization match before self-approved live execution.
9. **Select execution route.** Apply the Claude-first decision gate. Use Codex-local only for a recognized exception or an authorized takeover.
10. **Build the independent handoff.** Route packet construction and execution to `handoff-system`; dry-run before live and preserve the interface boundary.
11. **Persist runtime state.** Append hash-linked events and write Atomic Snapshots for every Story/Round. Publish only the safe status projection.
12. **Review execution and QA evidence.** Validate feedback, drift, unmapped actions, changed files, validation results and independent QA evidence.
13. **Route rework and enforce limits.** Return defects to the Artifact Owner; enforce no-progress, repeated-failure, invalid-feedback, timeout, round and resource limits.
14. **Coordinate optional concurrency.** Parallelize only independent Stories with isolated workspaces and write sets; gate every merge.
15. **Decide one state.** Use only the governed state set. Run `validate_transition`; run the CompletionEvaluator before `completed`.

## Landed Review And Publish Lifecycle

After an in-scope Story or Phase has implementation evidence, route through the
deterministic landed-review and manifest runtimes before any writeback or
publication:

1. Run `scripts/landed_review.py` against the immutable baseline and observed
   implementation manifest.
2. Treat `implementation-drift` as blocking. Treat semantic requirement change
   as `requirements-review` and create a new anchor; never edit the old anchor.
3. Candidate document revisions remain `need-review`; the runtime never creates
   RC or approval state.
4. Run `scripts/document_manifest_runtime.py` or its library contract to
   recompute content SHA-256 and validate publish state transitions.
5. Keep GitHub publication and GitBook synchronization as independent states;
   `gitbook-verified` requires explicit content-check evidence.

The local RAG writeback remains owned by `rag-intake`, `rag-schema`, and
`rag-governance`. This Skill may orchestrate them and compare their manifests,
but must not duplicate their material admission or RC rules.

Generic research now enters the research router; legacy Claude-specific execution gates apply to research-guided when Claude is selected. See [research execution gate](references/research-execution-gate.md).

## Routing Map

| Need | Route |
| --- | --- |
| Current/high-trust evidence, source gaps, tool capability checks | `research` |
| Hardening requirement choices or finding hidden assumptions | `grill-system` |
| PRD, development plan, test plan, RTM, acceptance criteria | `write-prd` |
| Skill structure, trigger design, validation, packaging readiness | `create-skill` |
| Phase/Story, role, Artifact, state or long-task governance | relevant bundled contract plus `development_runtime.py` |
| A2A packet and execution loop orchestration | `handoff-system` |
| Requirement-anchored packet construction | `handoff-packet-builder` |
| Claude Code dry-run/live adapter execution | `handoff-claude-executor` |
| Feedback packet review and drift classification | `handoff-feedback-reviewer` |
| UI-test or Midscene profile work | `ui-test` or a dedicated adapter profile |

## Phase Capability Map

| Phase | Capability |
| --- | --- |
| PH-01 | End-to-end governance contract, state, recovery, completion and hard gates |
| PH-02 | Claude-first single-Story live loop, preauthorization, visible state and takeover |
| PH-03 | Product, Architect, Planner, Engineer and QA profile pipeline |
| PH-04 | Ralph-style long-task runtime, checkpoint recovery and circuit governance |
| PH-05 | Isolated multi-Agent execution slots and merge gates |
| PH-06 | Safe observability, resource limits and audit reconstruction |
| PH-07 | MetaGPT module admission and additional Agent interface extension |

## CLW Adaptive Loop Capability Map

The `CLW-*` namespace is a separate product line and must not be inferred from
the historical `PH-*` or `DSCR-PH-*` identifiers above.

| CLW Phase | Capability | Entry gate |
| --- | --- | --- |
| CLW-PH-1 | Windows single-Claude, single-Story visible adaptive loop | approved CLW anchor |
| CLW-PH-2 | Serial Story DAG, aggregate recovery, budgets, circuit and Phase completion | CLW-PH-1 CompletionEvaluator passed |
| CLW-PH-3 | Windows isolated worktree slots, write-set and integration gates | CLW-PH-2 CompletionEvaluator passed |
| CLW-PH-4 | Independent Windows Agent profiles, capability/permission match and unified feedback review | CLW-PH-3 CompletionEvaluator passed |

Static contract preparation before an entry gate passes is not stage
completion and does not authorize live execution.

## Required Outputs

For a full loop, produce or update these artifacts:

- requirement anchor;
- reference coverage review and decision gate when research is used;
- PRD or requirements document;
- development plan;
- test plan or test handoff document;
- local direct implementation evidence when Codex executes without an external Agent;
- A2A handoff packet;
- execution feedback packet;
- Codex review with gap-to-requirement analysis;
- append-only Event History and Atomic Snapshot for long tasks;
- user-safe status and audit projections;
- CompletionEvaluator result;
- system-use retrospective when the user asks to evaluate `development-system` or after a substantial Skill development run;
- next-state decision and stop/approval status.

## Safety And Escalation

Stop and ask for approval before:

- any live Agent call that is not an exact match for active preauthorization;
- writing outside the approved workspace or data boundary;
- installing dependencies or plugins;
- changing global Codex, WorkBuddy, Claude, browser, or OS configuration;
- installing or overwriting a user-level Skill, even when the workspace candidate passed;
- publishing, deploying, deleting, migrating, or sending external messages;
- exposing sensitive data, credentials, repository contents, private screenshots, or production data.

Stop for requirements review when:

- a feedback packet is invalid or lacks evidence;
- execution actions are not mapped to FR/AC or confirmed decisions;
- P0/P1 drift is detected;
- the task needs a new requirement phase or profile;
- loop progress repeats without new evidence or a new root cause.

## References

- Read `references/router-contract.md` before using this skill as the top-level router.
- Read `references/control-plane-and-authority.md` before any control plane, authority order, internal profile or independent Skill boundary decision (PH1-ST-001).
- Read `references/metagpt-role-sop-contract.md` before role assignment, SOP stage entry/exit or artifact ownership decisions (PH1-ST-003).
- Read `references/artifact-lifecycle-contract.md` before creating, versioning or tracing any artifact to a requirement anchor (PH1-ST-002).
- Read `references/plan-story-contract.md` before decomposing a goal into phases and stories (PH1-ST-004).
- Read `references/handoff-interface-contract.md` before calling an independent Skill or reviewing its feedback (PH1-ST-005).
- Read `references/rework-and-gate-reopen-contract.md` before defect routing or upstream Artifact changes (PH1-ST-006).
- Read `references/event-history-and-recovery-contract.md` before checkpoint, resume or takeover decisions (PH1-ST-007).
- Read `references/state-and-completion-contract.md` before state transitions or completion review (PH1-ST-008).
- Read `references/long-task-runtime-contract.md` before multi-round Story execution (PH1-ST-009 and PH-04).
- Read `references/workspace-and-approval-contract.md` before workspace, preauthorization or installation decisions (PH1-ST-010 and PH-02).
- Read `references/claude-first-execution-contract.md` before choosing Claude, Codex-local or takeover (PH-02).
- Read `references/research-execution-gate.md` before accepting any research-backed evidence or routing a public-research Story to completion.
- Read `references/claude-governance-contract.md` before registry validation, preauthorization matching, auto-approval, dry-run-to-live transition, Chinese status projection, or bounded takeover (PH-2).
- Read `references/phase4-install-operations-contract.md` before compatibility assessment, backup/rollback preparation, installation approval, post-install validation or operations governance (DSCR-PH-4).
- Read `references/software-company-pipeline-contract.md` before activating Product, Architect, Planner, Engineer or QA Profiles (PH-03).
- Read `references/multi-agent-concurrency-contract.md` before starting concurrent execution slots or merging results (PH-05).
- Read `references/observability-and-resource-contract.md` before status display, budgets or governance reports (PH-06).
- Read `references/metagpt-module-admission.md` before adopting MetaGPT code or adding an Agent interface (PH-07).
- Read `references/phase4-controlled-loop.md` before planning live adapter loops.
- Read `references/clw-phase2-serial-orchestration-contract.md` before selecting or resuming multiple serial Stories in `CLW-PH-2`.
- Read `references/clw-phase3-isolated-concurrency-contract.md` before creating Windows execution slots, worktrees or merge candidates in `CLW-PH-3`.
- Read `references/clw-phase4-agent-extension-contract.md` before registering Midscene or another independent Agent profile in `CLW-PH-4`.
- Read `references/naming-and-boundaries.md` when deciding whether to route through this skill or directly through `handoff-system`.
- Read `references/requirement-anchor-template.md` before creating a saved requirement anchor for complex, schema, Skill, or A2A tasks.
- Read `references/phase1-boundary-contract.md` before Skill body development, workspace-copy decisions, live/dry-run/deploy approval design, or final-state classification.
- Read `references/local-direct-implementation-loop.md` before Codex performs a local implementation without Claude, Midscene, or another execution Agent.
- Read `references/local-global-skill-edit-loop.md` before changing any global Codex Skill.
- Read `references/landed-review-contract.md` before post-implementation document reconciliation.
- Read `references/document-manifest-contract.md` before manifest validation or publish-state transitions.
- Read `references/system-use-retrospective.md` when reviewing how this system performed during a real development run.
- Read `references/publish-package-contract.md` before staging, publishing, retrying, or independently verifying GitHub and GitBook delivery.

## Validation

Run from this Skill directory:

```powershell
python scripts/validate_development_system.py
python scripts/test_phase_story_contract.py
python scripts/test_development_runtime.py
python scripts/test_phase4_governance.py
python scripts/test_full_refactor_contract.py
python scripts/test_phase1_boundary_contract.py
python scripts/test_skill_governance_contract.py
python scripts/test_clw_phase2_phase4_runtime.py
python scripts/test_clw_phase2_serial_runtime.py
python scripts/development_runtime.py project-status-zh --state all
python scripts/development_runtime.py generate-ph2-fixtures --output-dir assets/fixtures
python scripts/development_runtime.py generate-ph2-change-record --output-dir .
```

Then run the generic `create-skill` validator with `--require-change-records`, a sensitive-data scan and a forward test. Workspace validation does not authorize user-level installation.

## PH-2 Capability

| Story | Capability |
|---|---|
| DSCR-ST-2-001 | Claude Agent registry with stable identity, capabilities, version, adapter, and completion-authority isolation |
| DSCR-ST-2-002 | Active preauthorization policy lifecycle with hash, expiry, and all-dimension boundary |
| DSCR-ST-2-003 | Exact-match auto-approval with redacted audit record; mismatches fail closed |
| DSCR-ST-2-004 | Dry-run-to-live transition gate that cannot be bypassed by a missing or mismatched manifest |
| DSCR-ST-2-005 | Stable machine state codes with Chinese status labels for all 11 governed states |
| DSCR-ST-2-006 | Bounded same-Story Codex takeover for unavailable/timeout/invalid feedback |

## DSCR-PH-4 Capability

| Story | Capability |
|---|---|
| DSCR-ST-4-001 | Compatibility matrix, source/target hashes, backup manifest and rollback readiness |
| DSCR-ST-4-002 | Exact, time-bounded user installation approval gate; workspace validation and dry-run never authorize installation |
| DSCR-ST-4-003 | Chinese status, resource/failure budgets, evidence retention and audit reconstruction |
