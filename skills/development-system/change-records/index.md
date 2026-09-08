# Development System Change Records

## Purpose

Track file-changing updates to `development-system` so future Codex runs can understand why the router changed, what evidence supported the change, and which validation gates passed.

## Latest Changes

| Date | Change ID | Summary | Status |
|---|---|---|---|
| 2026-09-08 | CR-20260908-003 | Research routing split candidate | validated / candidate only |
| 2026-08-25 | CR-20260825-001 | Add the research execution preflight, evidence and failure-propagation gate to the top-level router. | validated |
| 2026-08-24 | CR-20260824-003 | Set approval-gated default GitHub and GitBook targets and require exact GitBook binding in release approval. | validated |
| 2026-08-24 | CR-20260824-002 | Add the approval-gated live GitHub adapter, independent GitBook verification, public-scope allowlist and deterministic staging repair. | validated |
| 2026-08-24 | CR-20260824-001 | Add research-gated landed review, immutable candidate writeback, document manifest/state validation, and dry-run-first publish planning for the RAG/GitHub/GitBook lifecycle. | validated |
| 2026-08-20 | CR-20260820-001 | Route PRD generation from `development-system` to the new `write-prd` top-level router, align the requirements-to-plan fixture and validator terms, preserve `write-requirements-prd` as a downstream child skill, and normalize legacy detail records required by the generic Skill validator. | validated |
| 2026-08-17 | CR-20260817-007 | CLW PH-3 live packet exact policy schema, untracked nested write-set collection and Codex-owned live integration harness with candidate and regression evidence. | validated |
| 2026-08-17 | CR-20260817-005 | Align the aggregate PH-2 recovery test with the strict event/snapshot contract: stale pre-event snapshots fail and event-aligned snapshots pass. | validated |
| 2026-08-17 | CR-20260817-006 | CLW PH-3 Windows Git worktree identity, observed write-set, candidate hash and Codex-only integration runtime with real conflict/drift/regression tests. | validated |
| 2026-08-17 | CR-20260817-004 | CLW-ST-203 failure/resource budgets, three-state circuit (CLOSED/OPEN/HALF_OPEN), no-progress, failure fingerprint, invalid feedback, timeout recovery, resource budget, round limit, verified-progress evaluator and Phase completion gate; `development_runtime.py` unchanged. | validated |
| 2026-08-17 | CR-20260817-002 | CLW-ST-201 dedicated `assets/fixtures/clw-phase2` suite (4 positive, 7 negative) and deterministic `scripts/test_clw_phase2_serial_runtime.py` covering DAG, unique ID, known dependency, FR/AC mapping, stable selection, single-active, dependency blocker and false Agent completion; `development_runtime.py` unchanged. | validated |
| 2026-08-17 | CR-20260817-003 | CLW-ST-202 bounded Codex takeover repaired persisted snapshot schema and explicit Phase/queue recovery identity gates after Claude provider unavailability; dedicated recovery regressions pass. | validated |
| 2026-08-17 | CR-20260817-001 | CLW PH-2 serial queue/recovery, PH-3 isolated slot/write-set/merge-candidate and PH-4 Agent profile/capability/feedback-review deterministic contracts; live completion remains blocked by upstream gates. | validated |
| 2026-08-16 | CR-20260816-005 | CLW-ST-101 Story Profile and splitting gate: Story Profile schema (size, five deadlines, maxRounds), single-Story live handoff gate, Large Story split-required finding, positive and negative fixtures. | validated |
| 2026-08-16 | CR-20260816-004 | PH-4 compatibility, backup/rollback, exact user installation gate and operations/audit governance with deterministic schemas and negative fixtures. | validated |
| 2026-08-16 | CR-20260816-003 | PH-3 real closed-loop acceptance: bounded local live-loop harness (run_live_loop), feedback lineage validation (stale cycleId/storyId/roundNumber/attemptId detection), duplicate side-effect detection across rounds, eleven negative fixtures (spawn failure, timeout, invalid feedback, P1 drift, unmapped action, stale field, evidence gap, duplicate side effects, round limit, takeover limit, no-progress circuit), and validator coverage. CompletionEvaluator rejects Agent completed claims when any evidence, QA, permission, risk or drift gate is missing. | applied |
| 2026-08-16 | CR-20260816-002 | PH-2 Claude external Agent governance: registry, hash/expiry-bound preauthorization, exact auto-approval, hashed dry-run gate, Chinese state projection, bounded same-Story takeover, negative fixtures, and validator coverage. | validated |
| 2026-08-16 | CR-20260816-001 | Close the Artifact Envelope dual contract: validate_artifact_envelope now mirrors the normative schema required fields (createdAt, derivedFrom) instead of independently requiring sourceRefs and changeType. | validated |
| 2026-08-15 | CR-20260815-003 | Bind completion to hash-verified feedback evidence and align every runtime/reference/schema contract to the confirmed 11-state model after bounded Claude timeout takeover. | validated |
| 2026-08-15 | CR-20260815-002 | Complete PH1-ST-005 through PH7-ST-003 with deterministic runtime, schemas, references, negative fixtures, full-contract tests and bounded Claude-timeout takeover. | validated |
| 2026-08-15 | CR-20260815-001 | Require `mappedFrAc` in artifact envelopes after PH-01A regression; complete bounded Claude-timeout takeover evidence. | validated |
| 2026-08-14 | CR-20260814-001 | PH-01 foundation slice (ST-001~ST-004): control plane/authority, MetaGPT role SOP, artifact lifecycle, phase/story contracts; foundational schemas; positive and negative fixtures; validator and test script updates. | validated |
| 2026-08-09 | CR-20260809-003 | Repair generic Skill governance contract: add explicit Safety And Escalation heading, canonical Latest Changes index section, completed Phase 1 impact analysis, and regression coverage. | validated |
| 2026-08-09 | CR-20260809-002 | Add Phase 1 boundary contract for route, workspace-copy-first, approval gates, final-state decisions, fixture coverage, and validator enforcement. | validated |
| 2026-08-09 | CR-20260809-001 | Add local/global Skill edit loop, local direct implementation loop, requirement anchor template, system-use retrospective guidance, validator coverage, and change records. | validated |

## Category Index

| Category | Path |
|---|---|
| Core Skill MD | `change-records/categories/core-skill-md.md` |
| References And Assets | `change-records/categories/references-and-assets.md` |
| Scripts And Validation | `change-records/categories/scripts-and-validation.md` |
| Safety And Governance | `change-records/categories/safety-and-governance.md` |
| Downstream And Handoff | `change-records/categories/downstream-and-handoff.md` |

## Open Risks

- This workspace candidate is not installed to the user-level Skill directory; installation requires a new explicit approval.
- Concrete MetaGPT code modules remain `reference-only` until a pinned candidate passes the PH-07 admission gate.

Current candidate detail: [CR-20260908-003](entries/2026/2026-09/CR-20260908-003-research-routing.md).
