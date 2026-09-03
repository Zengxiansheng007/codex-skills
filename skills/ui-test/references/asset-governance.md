# UI-Test Project Asset Governance

## Scope

These rules apply only to UI-Test project assets. Ordinary workspace files, other Skill assets and global Skill program files are not governed by the D-drive double-root policy.

## Two Non-Overlapping Fact Domains

- Every automated functional branch has exactly one versioned Source Case v2 for test semantics and exactly one sibling `tests/test-data.json` v2 for manually editable business values and generation rules.
- Source Case stores steps, assertions, parameter IDs and typed references; it must not store the referenced business values. Test Data stores values and rules; it must not store locators, actions or assertions.
- Each Source Case v2 step carries one `module_id` and one or more explicit postconditions. A governed `PageModuleRegistry` declares each branch module as `operate`, `assert-default` or `not-applicable`; applicable P0 modules missing an immediate assertion block all projections.
- Human View, Midscene View, Resolved Case, parameter manifest and Python Playwright Test are deterministic projections. They carry `source_case_id`, `branch_id`, `source_hash`, `test_data_hash`, `parameter_manifest_hash`, `dependency_digest`, `build_fingerprint`, generator versions and `do_not_edit=true`.
- Human View uses the step columns `序号`、`操作`、`参数/数据`、`预期结果`; shared account and public data values must show an index or reference path instead of raw secrets.
- The product aggregate is rendered recursively from Case IR v2, Resolved IR v2 and strict manifests. Its fixed tree preserves project-group, product and system levels, emits common prerequisites once, and never concatenates case Human View Markdown.
- Never manually maintain the same case body or business value in multiple formats. Change Source Case for semantics, Test Data for business values/rules, or a shared Flow/Page/Component/binding for automation mechanics; then run plan/sync and validate the active release.
- A non-`in_sync` active release cannot execute, report, write experience, migrate as active, or complete.

## Storage

- Execution assets: `D:\UI-Test` only.
- Knowledge, experience and redacted evidence indexes: `D:\RAG` only.
- Staging and model exploration output: `D:\UI-Test\_tmp` or a governed run staging path.
- The project must supply `ui-test.project.yaml` v2 with both roots, stable IDs, display names, system/module/function registry, wait strategy and policy references.
- The project config must declare scoped private `runtime_value_index_ref` and `credential_index_ref` references plus named `runtime_refs`; callers resolve URL and switches through `RuntimeValueLoader` and credentials through the separate credential loader, while legacy `env_ref` names are metadata only.
- `runtime-value-index.yaml` stores environment Runtime values, switches, exploration values and cross-run sequence state; `credential-index.yaml` stores platform-level account credentials; branch `test-data.json` stores case business values and rules. These sources have independent schemas and hashes.
- The Path Planner chooses the root from registered asset type. Callers must not supply `root`, `target_root`, `output_dir` or an arbitrary formal target.
- Use `stable-id__display-name` for business path segments and the fixed hierarchy `project_group/product/system/module_path/function/case/branch/run`.
- Reject C-drive formal UI-Test project assets, root/type mismatch, lexical escape, symlink, junction or reparse-point traversal. Do not report an ordinary C-drive workspace document as a UI-Test violation.

## Case Structure

- Priority is P0, P1 or P2. A P0 page smoke suite may contain multiple user-confirmed branch cases whose declared responsibilities jointly cover all registered primary test points and applicable component variants.
- Separate `setup`, `feature` and `assertions`. A setup failure is `setup/navigation failure`, not a target feature defect.
- Shared login/navigation belongs in versioned Flow objects. Locators and page operations belong in Page/Component objects. Thin tests contain identity, markers and one scenario call; they do not copy locators.
- System announcement plain content and popup announcement rich content are separate Component variants and cannot silently share a binding.

## Compilation And Execution

- The Case Compiler is fixed Python code. Formal plan/sync never calls a model or network to change generated content.
- New writes use the v2 contract family. V1 Source Case, IR, manifests, receipts, releases, runs and reports remain audit-readable but cannot regain execution eligibility without a controlled successor migration.
- Use Draft 2020-12 validation, RFC 8785 canonical hashing, explicit dependency/reverse indexes, immutable releases, expected-active checks and readback validation.
- A v2 manifest enumerates every non-self release attachment. Release integrity, current input sync and execution readiness are independent axes; current drift is never written back into an immutable release.
- Formal semantic successors are published inactive first. A matching `PreSubmitQualificationResult` must prove all non-submit steps and module assertions passed, screenshot evidence is hash-bound, `submit_count=0`, `write_state=not_attempted` and `sequence_allocated=false` before atomic activation.
- Formal regression uses only Python + pytest + pytest-playwright. Each test file and node ID must run independently and as part of the suite; filenames must be unique.
- Every formal test gets a fresh BrowserContext and executes the complete login/menu/function Flow. Midscene exploration may use a current-session ready checkpoint route, but a formal Playwright test never skips the full precondition Flow.

## R2 And Results

- R2 approval is current-run, test-environment and visible-UI only. API business writes, production writes and a second submit are blocked.
- Required fields and date controls must be deterministically valid before R2 authorization; otherwise fail before consuming the submit allowance.
- Visible client-side required validation after the only click is `write_failed`; a unique list record is `write_succeeded_verified`; success feedback without list verification is `write_succeeded_verification_failed`; absent deterministic signals remain `write_outcome_unknown`.
- A write success followed by verification failure is `write_succeeded_verification_failed`; do not compensate, delete or submit again.
- Teardown releases browser and trace resources only. Created business data is retained with `cleanup_status=not_planned_this_release`.
- Canonical RunResult is the only result truth. Evidence, report, metrics and experience are read-only projections and cannot upgrade status or grant permission.
- A historical unknown write outcome may be diagnosed only through a new hash-bound `ui-test.run-reconciliation.v1` record. Reconciliation is diagnostic-only, keeps the canonical RunResult unchanged and never grants rerun authorization.

## Required Gates

Before write: project config v2, Packet v2, Source/IR Schema, migration issue, sensitive scan, Path Plan and `in_sync` checks.

After write/run: scan produced paths and formal references, validate hashes and release status, then produce RunResult and projections. Any stable P0/P1 issue blocks completion.
