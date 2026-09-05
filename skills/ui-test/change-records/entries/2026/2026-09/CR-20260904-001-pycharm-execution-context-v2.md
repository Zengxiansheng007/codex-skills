# CR-20260904-001 - PyCharm Execution Context V2 Schema And Version Migration

| Field | Value |
|---|---|
| Status | applied |
| Target Skill | ui-test workspace candidate |
| Change Type | contract / schema / migration / governance |
| Scope | core-skill-md / references-and-assets / scripts-and-validation / safety-and-governance / downstream-and-handoff |
| Source | user-approved PyCharm execution governance requirements (UIT-PYCHARM-GOV-20260903) |
| Baseline | ui-test workspace candidate 195-file zero-diff copy on 2026-09-03 |
| Author | Codex |
| Related Records | CR-20260902-001, CR-20260902-002, CR-20260903-001 |

## Summary

Add versioned schemas for v2.1 project config, ExecutionContextV2, ExecutionAttemptV1, R2ApprovalRecordV2 and RunResultV4 with positive/negative fixtures, tests, contract-registry migration and change-record ledger updates. Historical schemas remain read-only and deprecated for execution.

## Context And Problem

The existing v2.0 project config, v1 R2 approval record and v3 RunResult lack the fields required to enforce unified execution context, per-node attempt lifecycle, separated approval-source identity and layered status. Codex could display "passed" for unit/release/qualification tests while the PyCharm formal entry failed. The v2.0 pycharm_manual_execution contract only had two boolean flags and could not encode the six required execution-governance fields.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `schemas/ui-test-project-v2.1.schema.json` | project config | Add v2.1 schema with contract_version, origin_detection, entry_scope, r2_authorization, run_scope and r2_parallelism in pycharm_manual_execution. |
| `schemas/execution-context-v2.schema.json` | execution context | Add ExecutionContextV2 with origin, origin_evidence, run/node/case/branch/risk/environment, approval, stable runner/active/config digests and relative attempt_ref. |
| `schemas/execution-attempt-v1.schema.json` | attempt lifecycle | Add ExecutionAttemptV1 with diagnostics_admission, append-only events, unique terminal, unfinished/interrupted/unresolved recovery and relative evidence_refs. |
| `schemas/r2-approval-record-v2.schema.json` | approval record | Add R2ApprovalRecordV2 with approval_source, node_id, branch_id, risk_level, stable_runner_digest and active digests. |
| `schemas/run-result-v4.schema.json` | run result | Add RunResultV4 with execution_context_ref/hash, attempt_ref/hash, approval_ref/hash, write_state, submit_count and layered_status. |
| `schemas/contract-registry.json` | contract registry | Register five new active contracts and deprecate project.v2, r2-approval-record.v1 and run-result.v3 to read-only audit. |
| `assets/fixtures/*.json` | fixtures | Add valid and negative fixtures for all five new schemas. |
| `tests/test_execution_context_v2_schemas.py` | regression tests | Add positive and negative schema validation, historical-unchanged assertions and v2.0 execution-eligibility gate tests. |
| `tests/test_v2_schema_registry.py` | registry tests | Update assertions to reflect v2.1 deprecation of v2.0 project, v1 approval and v3 run-result contracts and new active contracts. |
| `scripts/ui_test_core/pycharm_runtime.py` | execution origin and Run ID | Classify PyCharm/Codex/CLI/CI channels from safe evidence, generate per-node IDs and remove the fixed fallback. |
| `scripts/ui_test_core/pycharm_runtime.py` | PyCharm 2025.3 real entry repair | Detect the exact existing JetBrains runner through `__main__.__file__` when the helper has rewritten argv; keep environment hints and ordinary arguments non-authoritative. |
| `scripts/ui_test_core/pycharm_runtime.py` | PyCharm 2025.3 Windows process-entry repair | Read the immutable Windows process command line and accept only argv[1] as an exact existing JetBrains runner after PyCharm also rewrites `__main__.__file__`; reject later-argument spoofing. |
| `scripts/ui_test_core/pycharm_runtime.py` | PyCharm TeamCity transport precedence repair | Keep strong CI markers first, but let an exact JetBrains runner outrank PyCharm's local `TEAMCITY_VERSION`; retain TeamCity CI classification when no runner exists. |
| resolver, schemas, fixtures and Tianjin authorization/finalizer | approval-source contract correction | Use the approved stable machine value `pycharm-project-policy` for policy-derived current-node PyCharm R2; retain `explicit-cli` for CLI/CI and remove the unapproved `pycharm-manual-run` value. |
| `tests/test_pycharm_runtime.py` | resolver regression | Cover strict runner paths, CI precedence, v2.1 policy, explicit CLI behavior and unique IDs. |
| `scripts/ui_test_core/pytest_runtime_plugin.py` | pytest plugin (ST-004) | Add universal pytest plugin: CLI options, hookspec, marker validation, per-node ExecutionContextV2 stash, fixture. No R2 lock or attempt creation. |
| `scripts/ui_test_core/r2_project_lock.py` | R2 cross-process lock (ST-005) | Add session-local Windows named Mutex non-blocking serial lock with SHA-256 scope derivation, fail-closed release, acquire/release/context manager, xdist detection and R3 blocking. |
| `scripts/ui_test_core/pytest_runtime_plugin.py` | R2 lock integration (ST-005) | Integrate R2 lock acquisition in pytest_runtest_setup, teardown release via hookwrapper, R3 E_R3_BLOCKED and xdist E_R2_PARALLEL_FORBIDDEN. |
| `tests/test_r2_project_lock.py` | R2 lock tests (ST-005) | Add unit and integration tests: first acquire, conflict, release reacquire, abandoned recovery, R0/R1 bypass, R3/xdist reject, teardown release. |
| `scripts/ui_test_core/execution_attempt_store.py` | attempt store (ST-006) | Add append-only ExecutionAttemptStore with controlled evidence_root, exclusive-create attempt-start and per-diagnostic files, append-only phase events, exclusive-create unique terminal, recovery event append, unfinished projection, history hash verification and sensitive content detection. |
| `scripts/ui_test_core/completion_projector.py` | completion projector (ST-006) | Add six-layer CompletionProjector: unit, collection, release_verification, qualification, pycharm_integration, human_r2; completed=false until all passed and no P0/P1/unknown; functional-accepted / repair-needed for incomplete governance evidence. |
| `scripts/ui_test_core/attempt_recovery.py` | attempt recovery (ST-006) | Add AttemptRecovery: scan unfinished attempts, append interrupted/unresolved recovery events, injectable PID/host/time functions, no terminal forgery, no new-run blocking, previous-attempt-unknown warnings. |
| `scripts/ui_test_core/pytest_runtime_plugin.py` | attempt lifecycle integration (ST-006) | Add required execution evidence root hookspec, diagnostics in collection for early gate failures, attempt-start creation after R2 lock/setup, official TestReport-based setup/call/teardown recording, recovery scan and unique terminal generation after teardown. |
| `scripts/ui_test_core/pytest_runtime_plugin.py` | qualification finalizer boundary (ST-011 repair) | Keep attempt and terminal for `--ui-pre-submit-only`, but skip the ordinary RunResultV4 finalizer because qualification intentionally has no R2 approval record or run-result-pending; normal runs retain fail-closed finalization. |
| `scripts/ui_test_core/pytest_runtime_plugin.py` | failed-terminal finalizer boundary | Invoke the successful business RunResultV4 finalizer only for passed terminals; preserve failed/timed-out call evidence without a second missing-pending teardown error. |
| `schemas/execution-attempt-v1.schema.json` | attempt schema fix (ST-006) | Make terminal optional so unfinished attempts can be represented; existing terminal still must conform to unique terminal. |
| `tests/test_execution_attempt_store.py` | attempt store tests (ST-006) | Add fault injection and pytester tests: early gate zero attempt, setup/call/teardown unique terminal, cancel/timeout mapping, kill leaves unfinished, recovery interrupted/unresolved with history hash unchanged, duplicate terminal rejected, previous unknown not blocking, six-layer completion gate. |
| `project-adapter/formal_conftest.py` | Tianjin pytest root (ST-007) | Explicitly load the universal plugin, expose project/stable/active/evidence hooks, remove duplicate Run ID/R2 option ownership and inject ExecutionContextV2 into the runtime. |
| `project-adapter/formal_identity.py` | active identity resolver (ST-007) | Resolve the exact branch active release, verify manifest/artifact identity and return build plus raw stable-runner digests without paths. |
| `project-adapter/formal_authorization.py` | node authorization and Approval V2 (ST-007) | Interpret pending as no standing authorization, bind origin to current-node approval source, require test/R2 policy and construct R2ApprovalRecordV2 directly. |
| `project-adapter/formal_runtime.py` | context consumer (ST-007) | Consume only ExecutionContextV2 for Run/approval identity, defend v2.1 at runtime, bind node/attempt/build and remove V1 approval adaptation. |
| `project-adapter/tests/test_*.py` | adapter offline gates (ST-007) | Add executable active identity, source ownership, node binding, pending matrix and Approval V2 Schema tests. |
| `project-adapter/ui-test.project.v2.1.yaml` | governed config source (ST-008) | Preserve the current Tianjin v2.0 business/config identities and add only the v2.1 PyCharm execution contract fields. |
| `project-adapter/formal_deploy.py` | successor lifecycle (ST-008) | Compile from the adapter config source, stage config/runners during prepare, retain active, require two zero-submit qualifications, preserve history hash and emit hash-bound readiness after CAS activation. |
| `project-adapter/formal_runtime.py` / `formal_conftest.py` | terminal-after result finalization (ST-008) | Persist a non-final business observation during call and create immutable RunResultV4 only after the pytest terminal and final attempt hash exist. |
| `scripts/ui_test_core/run_evidence_linker.py` | RunResultV4 binding (ST-008) | Bind snapshot/context/attempt/approval refs and hashes, reject path traversal and keep all V3 entrypoints unchanged. |
| `schemas/pycharm-governance-readiness-v1.schema.json` | activation readiness (ST-008) | Require candidate/global-install evidence hashes, two case builds, two qualification results, equal history hashes and four pre-human passed layers. |
| `project-adapter/tests/test_st008_*.py` | controlled deployment tests (ST-008) | Execute real tmp prepare/activation and terminal-after-finalizer flows without browser, D-drive or global writes. |
| `tests/test_pytest_runtime_plugin.py` | plugin pytester tests (ST-004) | Add pytester/fake-item tests: explicit load, --trace-config, normal tests unaffected, per-node context, marker missing/conflict, v2.0 block, CLI no-ID, PyCharm source, active resolver. |
| `tests/test_pytest_runtime_plugin.py` | qualification finalizer regression (ST-011 repair) | Prove pre-submit mode skips a failing project finalizer while the same finalizer still makes an ordinary run teardown fail. |
| `assets/source-baseline.json` | governed Skill baseline (ST-011 repair) | Refresh the exact `SKILL.md` SHA-256 after documenting the qualification finalizer boundary. |
| `SKILL.md` | project governance, decision rules, escalation | Require the root pytest plugin, v2.1 execution gate, origin/approval separation and layered completion. |
| `references/asset-governance.md` | Execution Context Governance | Define stable-entry, cross-process R2, diagnostics/attempt and accepted-risk boundaries. |
| `references/execution-contracts.md` | Execution Governance Separation | Prevent pytest, business write, human acceptance and overall completion states from substituting for one another. |
| `references/workflow-contract.md` | exit criteria | Require layered status evidence and manual A/B R2 before overall completion. |
| `change-records/index.md` | change-record index | Add CR-20260904-001 entry. |
| `change-records/categories/*.md` | category ledgers | Update references-and-assets, scripts-and-validation, safety-and-governance and downstream-and-handoff ledgers. |

## Decision And Alternatives

Use new schema versions (v2.1, v2, v1, v2, v4) instead of modifying historical schemas. This preserves audit readability of v2.0/v1/v3 and follows ADR-005. The alternative of mutating existing schemas was rejected because it would break historical release/RunResult immutability and violate NFR-004.

## Detailed Change

- `ui-test-project-v2.1.schema.json`: Extends v2.0 with a strict `pycharm_manual_execution` block requiring `contract_version=2`, `origin_detection=jetbrains-runner-path`, `entry_scope=stable-active-runners`, `r2_authorization=auto-test-only`, `run_scope=per-node`, `r2_parallelism=serial-project-environment`. `additionalProperties=false` ensures unknown fields fail closed.
- `execution-context-v2.schema.json`: All evidence and attempt references use `not` patterns to reject absolute paths (`C:\`, `/`, `\`). `origin_evidence.argv0` is also relative-only. No credential fields exist in the schema.
- `execution-attempt-v1.schema.json`: Events use `detected/admitted/executing/terminal/interrupted/unresolved/unfinished` enum. `recovery` is optional and append-only. `terminal.is_unique_terminal` is `const: true`. `evidence_refs` items reject absolute paths.
- `r2-approval-record-v2.schema.json`: Requires `approval_source`, `node_id`, `branch_id`, risk and active-entry identity beyond v1 fields. `environment` is `const: test`; the risk enum excludes R3.
- `run-result-v4.schema.json`: Requires `execution_context_ref/hash`, `attempt_ref/hash`, `approval_ref/hash`, `write_state`, `submit_count` and `layered_status` with six layers (unit, collection, release_verification, qualification, pycharm_integration, human_r2). All ref fields reject absolute paths.
- Contract registry: five new contracts registered as `active`; three old contracts deprecated.
- Fixtures: 4 valid, 12 file-backed negative fixtures plus 2 in-memory sensitive-shape mutations covering missing fields, unknown enums, v2.0 execution, absolute paths and R3 approval.
- Focused tests: 39 tests cover the five Schema families, registry migration and origin resolver.
- Runtime resolver: source classification is separated from approval, environment hints alone cannot create a PyCharm origin, and missing non-PyCharm IDs remain missing.
- Skill and references: the pytest plugin is the sole context control layer; project runtimes consume validated contexts; layered states cannot upgrade one another.

## Impact Analysis

All new schemas are additions; no historical schema file is modified. The contract registry status changes affect registry tests but do not change historical files. Normative Skill/reference changes make the v2.1 plugin path mandatory for future formal execution while leaving installation and deployment separately gated.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Schema meta-validation | `test_execution_context_v2_schemas.py` | passed by Codex | 27 focused tests total passed |
| Positive fixture validation | Draft202012Validator.validate for valid fixtures | passed by Codex | Included in focused suite |
| Negative fixture rejection | Draft202012Validator.validate for file and in-memory negatives | passed by Codex | Included in focused suite |
| Contract registry | `test_v2_schema_registry.py` | passed by Codex | Included in focused suite |
| Skill/change record structure | `validate_create_skill.py --require-change-records` | accepted-with-constraints, 0 findings | Codex independent validation |
| Resolver and Schema focused suite | `test_pycharm_runtime.py` plus ST-001 tests | 39 passed | Codex bounded takeover after no-progress timeout |
| Skill/reference structure | `validate_create_skill.py --require-change-records` | accepted-with-constraints, 0 findings | Codex review after ST-003 |
| Candidate sensitive scan | `scan_sensitive_assets.py` | clear, 0 findings | Codex review after ST-003 |
| Pytest plugin merged regression | plugin, project loader, resolver and Schema tests | 65 passed | Codex semantic-review takeover after Claude feedback gaps |
| R2 lock focused regression | lock, plugin, resolver, project path and Schema tests | 91 passed | Codex repaired false same-thread conflict coverage, real abandoned-process coverage and release failure reporting |
| ST-005 Skill structure and sensitive scan | Skill validator plus sensitive asset suite | 0 findings; 8 sensitive tests passed | Candidate-only independent validation |
| ST-006 lifecycle regression | attempt, recovery, Completion, plugin, lock, resolver, project path and Schema tests | 138 passed | Codex repaired 8 initial failures and added real hard-exit, setup/call/teardown, timeout/cancel and concurrent diagnostics coverage |
| ST-007 project adapter regression | complete `project-adapter/tests` suite | 92 passed | Codex repaired 8 initial failures plus deployed-root resolution, direct Approval V2 construction and executable pending/source matrix |
| ST-007 adapter sensitive scan | `scan_sensitive_assets.py project-adapter` | clear, 0 findings | No private values or authorization material persisted |
| ST-008 deployment lifecycle | real tmp prepare and activation flows | 2 passed | Active retained during prepare; two successor releases, config/runners, qualification binding, activation readiness and history hash verified |
| ST-008 terminal finalizer | deployed-shape tmp finalizer | 1 passed | No V4 before terminal; terminal-after V4 and evidence index passed Schema/hash gates |
| ST-008 merged focused suite | V4/config/plugin/attempt/Schema/linker | 113 passed | Includes resolver, context persistence, traversal rejection and readiness Schema |
| ST-010 first installation attempt | global post-install full suite | 373 passed, 15 failed; automatically rolled back | Cross-project ST-008 tests were incorrectly packaged inside the global Skill and required a workspace sibling adapter |
| ST-010 rollback verification | restored global full suite | 243 passed | Restored 195-file ordinal-tree baseline hash exactly; failed 231-file candidate retained in backup |
| ST-010 packaging repair | self-contained candidate plus project adapter | 364 passed; 98 passed | Removed the cross-project test from the global package; real deployment/trace/finalizer coverage remains in project-adapter tests |
| ST-011 qualification preflight repair | focused pytester boundary | 2 passed | Qualification skips ordinary RunResult finalization; normal run remains fail closed |

## Safety And Privacy

No credential values, credential-shaped assignments, authorization headers or private URLs are stored in any schema, fixture or test. Sensitive-shape negative values are assembled only in test memory from split literals. The `execution-context-v2` schema explicitly rejects absolute paths for `argv0`, `attempt_ref` and `evidence_refs`. The `run-result-v4` schema rejects absolute paths for all ref fields. Fixtures use zero-hash placeholders (`sha256:000...`) to avoid real artifact hashes.

## Risks And Follow-up

- Full candidate validation remains deferred until ST-008/ST-009; focused validation cannot authorize installation.
- The `execution-context-v2` `config_summary` is optional to allow contexts where config is not yet loaded; runtime must reject contexts without a matching config_summary before R2 authorization.
- ST-001 through ST-008 are applied and focused-validated in the workspace candidate. ST-008 uses the current formal v2.0 file as the business/config baseline and adds only v2.1 execution governance; an initially invented configuration was rejected by the real prepare test. Prepare stages the new config, adapter and runners while leaving active untouched. Qualification identity requires an explicit mode/build and activation requires two zero-submit results plus candidate/global-install evidence hashes. Readiness no longer uses self-authored booleans and binds case/product builds, qualifications and equal before/after history hashes. Runtime writes only a pending business observation during call; the project finalizer creates RunResultV4 after the unique terminal and final attempt hash. Full candidate validation and protected installation/deployment/human stages remain incomplete, so this record must not be marked validated yet.
- ST-010 first installation reached readback but failed the mandatory installed-package full suite because `tests/test_st008_v21_deployment_v4.py` depended on a workspace sibling `project-adapter`. The governed rollback restored the exact 195-file global baseline and 243/243 tests. The candidate was repaired by removing that cross-project test from the global package; generic context/V4/linker coverage remains in self-contained tests, while the real prepare/activation/trace/finalizer coverage remains in `project-adapter/tests`. The repaired 230-file candidate passes 364/364 self-contained tests and the project adapter still passes 98/98. Because the source hash changed, ST-010 remains `blocked-user-decision` pending a new exact installation approval.
- ST-011 live qualification preflight found that the plugin called the ordinary RunResultV4 finalizer after a successful `--ui-pre-submit-only` call. Because qualification intentionally creates QualificationResult rather than R2ApprovalRecord/run-result-pending, this would have produced a false teardown error after real private UI work. The workspace repair skips only that finalizer in pre-submit mode, retains attempt/terminal, and adds a negative guard proving normal runs still fail closed. Real UI was not started and the prior qualification approval was not consumed.

Refs: UIT-PYCHARM-GOV-20260903; PRD-UIT-PYCHARM-001; ARCH-UIT-PYCHARM-001; DEV-UIT-PYCHARM-001.
