# Safety And Governance Change Ledger

## Purpose

Track changes to approval gates, global-write boundaries, privacy, completion control, and governance records.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-08-24 | CR-20260824-003 | default release target / GitBook approval gate | safety / governance | Keep defaults non-authoritative and require exact GitBook organization, Site and Space approval. | validated |
| 2026-08-24 | CR-20260824-001 | landed review / publish preflight / external boundary | safety / governance | Fail closed on sensitive input, drift, approval mismatch and unverified GitBook status. | validated |
| 2026-08-20 | CR-20260820-001 | references/control-plane-and-authority.md / references/phase1-boundary-contract.md | governance | Repoint PRD routing authority to `write-prd` while keeping `write-requirements-prd` as a child skill. | validated |
| 2026-08-17 | CR-20260817-001 | CLW stage entry, completion, worktree and Agent authority gates | safety / governance | Keep upstream completion gates fail-closed and isolate Agent/profile authority from Codex completion. | validated |
| 2026-08-16 | CR-20260816-004 | install approval / backup / operations | safety / governance | Require exact user approval and rollback evidence; dry-run never installs. | validated |
| 2026-08-16 | CR-20260816-003 | completion / drift / limits | safety / governance | Prevent Agent claims, stale lineage and duplicate side effects from completing. | applied |
| 2026-08-16 | CR-20260816-002 | preauthorization / dry-run / takeover / manual gates | safety / governance | Fail closed on inactive, expired, tampered or enlarged policies and bound Codex takeover to the same Story. | validated |
| 2026-08-15 | CR-20260815-003 | CompletionEvaluator / governed state authority / takeover scope | repair / safety / governance | Prevent completion bypass through unverified feedback and prevent undeclared runtime-state expansion after Claude timeout takeover. | validated |
| 2026-08-15 | CR-20260815-002 | preauthorization / CompletionEvaluator / circuit / installation gate | safety / governance | Permit self-approval only on complete policy match, reject Agent completion authority and retain explicit user approval for installation. | validated |
| 2026-08-14 | CR-20260814-001 | control plane authority / ownership boundary | safety / governance | Freeze Codex sole control plane authority; enforce independent Skill ownership and private profile boundaries via schema and negative fixtures. | validated |
| 2026-08-09 | CR-20260809-003 | safety heading / change-record completeness | governance | Align explicit safety labeling and traceability records with generic Skill governance checks. | validated |
| 2026-08-09 | CR-20260809-002 | workspace-copy-first / approval boundary / final-state rules | safety / governance | Make workspace-copy-first mandatory for multi-file, high-risk, global Skill, and single-file behavior changes; codify approval and final-state gates. | validated |
| 2026-08-09 | CR-20260809-001 | approval / governance | governance | Make global Skill deployment and post-run retrospective evidence explicit. | validated |

## Detailed Records

### CR-20260824-003 - default-publish-targets

- Section changed: release target approval boundary.
- Before: repository, branch, visibility and path roots were approval-bound, but GitBook IDs were runtime-only arguments.
- After: GitBook organization, Site and Space must be present in and equal to the approval object.
- Why: a convenient default must not silently authorize an external destination.
- Impact: wrong or stale GitBook bindings stop before GitHub publication begins.
- Validation: mismatch regression, sensitive-data scan, approved global deployment and post-install validation passed.
- Detail record: `change-records/entries/2026/2026-08/CR-20260824-003-default-publish-targets.md`

### CR-20260816-002 - ph2-claude-governance

- Section changed: Claude approval and recovery governance.
- Before: literal dry-run status and implicit Story identity could satisfy partial checks.
- After: hashed manifests, exact policy identity and explicit lineage are mandatory; installation and new boundaries remain manual.
- Why: automatic approval must not expand authority or create an unbounded fallback.
- Impact: in-boundary execution is automatic while mismatch and high-risk operations stop.
- Validation: expiry, tamper, dry-run, threshold, budget and cross-Story negative cases passed.
- Detail record: `change-records/entries/2026/2026-08/CR-20260816-002-ph2-claude-governance.md`

### CR-20260820-001 - write-prd-router-entry

- Section changed: `references/control-plane-and-authority.md` and `references/phase1-boundary-contract.md`.
- Before: the PRD route named `write-requirements-prd` as the independent skill boundary.
- After: `write-prd` is the routed PRD entry point and `write-requirements-prd` is documented as a downstream child skill.
- Why: the new topology keeps the router entry and the PRD authoring skill distinct.
- Impact: safety and authority guidance now matches the new route name.
- Validation: workspace and deployed global validation passed after backup and global deployment.
- Detail record: `change-records/entries/2026/2026-08/CR-20260820-001-write-prd-router-entry.md`

### CR-20260815-003 - completion-evidence-and-state-alignment

- Section changed: CompletionEvaluator evidence requirements and governed state authority.
- Before: a nominal feedback-valid flag could be mistaken for independently validated feedback; a workspace-only cancellation state was not authorized by DS-PSR-001.
- After: Codex completion requires hash-bound external validation evidence, and only the confirmed 11 states are accepted. Claude timeout/takeover remained bounded to the approved workspace; an unauthorized generated `run_tests.bat` was removed.
- Why: preserve Codex control-plane authority and fail closed on premature completion and silent scope expansion.
- Impact: adapter claims, timeouts, resource signals and undeclared states cannot produce `completed`.
- Validation: negative completion/state fixtures, runtime/full-contract tests, specialized validator and sensitive scan passed.
- Detail record: `change-records/entries/2026/2026-08/CR-20260815-003-completion-evidence-and-state-alignment.md`

### CR-20260815-002 - full-runtime-ph1b-ph7

- Section changed: execution authorization, state transition, completion, circuit and installation boundaries.
- Before: live approval rules were coarse and later Phase safety requirements were not executable.
- After: six-dimensional preauthorization, Codex-only transition, CompletionEvaluator, timeout/takeover, round/circuit/resource limits and installation approval are enforced in code and negative fixtures.
- Why: prevent silent permission expansion, infinite loops and premature completion.
- Impact: in-boundary development can proceed automatically, while scope mismatch and user-level installation fail closed.
- Validation: authorization, transition, completion, circuit and installation negative fixtures passed.
- Detail record: `change-records/entries/2026/2026-08/CR-20260815-002-full-runtime-ph1b-ph7.md`

### CR-20260814-001 - ph1-foundation-slice

- Section changed: control plane authority rule, ownership boundary contracts, negative ownership fixture.
- Before: the first non-negotiable rule did not explicitly state "sole control plane and completion authority"; no negative fixture proved ownership conflicts are rejected.
- After: SKILL.md states "Codex is the sole control plane and completion authority"; control-plane-and-authority.md defines authority order, independent Skill table and private profiles; NEG-OWNERSHIP-001 fixture proves same-name global skill clash is rejected.
- Why: AC-001 requires that conflicting control or same-name global role skills are rejected by the validator.
- Impact: future agents and validators have a deterministic ownership boundary.
- Validation: phase/story contract test and development-system validator passed.
- Detail record: `change-records/entries/2026/2026-08/CR-20260814-001-ph1-foundation-slice.md`

### CR-20260809-003 - generic-skill-governance-contract

- Section changed: safety/escalation labeling and governance record completeness.
- Before: the approval content was present but not recognized as a safety section; one earlier record omitted its impact analysis.
- After: safety is explicitly labeled and the prior Phase 1 record states its impact on routing, approval, and completion control.
- Why: governance validation must see both policy and traceability evidence.
- Impact: the Skill's existing approval boundaries become reviewable through a consistent contract.
- Validation: RED test reproduced the generic validator failure; GREEN validation passed in workspace and global validation.
- Detail record: `change-records/entries/2026/2026-08/CR-20260809-003-generic-skill-governance-contract.md`

### CR-20260809-002 - phase1-boundary-contract

- Section changed: workspace-copy-first scope, approval boundary template, and final-state decision table.
- Before: approval and completion rules existed, but Phase 1 did not have a single hard boundary contract.
- After: the boundary contract defines mandatory workspace-copy triggers, direct edit exception, approval fields, and state evidence conditions.
- Why: prevents unsafe direct edits and premature completion in future Skill development.
- Impact: stricter safety gates for behavior-changing Skill work.
- Validation: Phase 1 boundary test and development-system validator passed.
- Detail record: `change-records/entries/2026/2026-08/CR-20260809-002-phase1-boundary-contract.md`

### CR-20260809-001 - development-system-local-global-loop

- Section changed: global Skill edit workflow and retrospective guidance.
- Before: Approval gates existed, but the safe global Skill edit sequence was not detailed.
- After: The global Skill edit loop requires workspace edits, approval before global deployment, backup when practical, deployed validation, and final record update.
- Why: Global Skill edits are high-impact and need repeatable evidence before completion.
- Impact: Reduces risk of workspace/global drift and premature completion.
- Validation: Source validation and sensitive-data scan passed.
- Detail record: `change-records/entries/2026/2026-08/CR-20260809-001-development-system-local-global-loop.md`
### CR-20260816-004 - ph4-install-operations-governance

- Section changed: user-level installation and operations governance.
- Before: installation remained manual but lacked an exact executable approval object.
- After: source, target, coverage, backup, rollback and time window must match.
- Why: prevent workspace success from silently authorizing a global write.
- Impact: this run cannot install without a separate user approval.
- Validation: negative approval tests passed; final suite pending.
- Detail record: `change-records/entries/2026/2026-08/CR-20260816-004-ph4-install-operations-governance.md`

### CR-20260816-003 - ph3-real-closed-loop

- Section changed: CompletionEvaluator inputs, lineage and bounded loop checks.
- Before: PH-2 primitives lacked a single closed-loop safety decision.
- After: drift, evidence, QA, permissions, side effects and budgets all block completion when invalid.
- Why: Agent output is evidence, not completion authority.
- Impact: PH-3 live timeout remains blocked rather than falsely completed.
- Validation: deterministic matrix passed; live positive remains open.
- Detail record: `change-records/entries/2026/2026-08/CR-20260816-003-ph3-real-closed-loop.md`

### CR-20260908-003 - Research routing split

- Section changed: approved candidate routing/identity boundary.
- Before: generic research was the Claude execution entry.
- After: generic router and retained guided execution are separate.
- Why: approved research-routing review.
- Impact: development-system; no global writes.
- Validation: candidate evidence in development workspace; initially pending.
- Detail record: [record](../entries/2026/2026-09/CR-20260908-003-research-routing.md).
