# UI-Test Project Asset Governance

## Scope

These rules apply only to UI-Test project assets. Ordinary workspace files, other Skill assets and global Skill program files are not governed by the D-drive double-root policy.

## Single Source Of Truth

- Every automated functional case has exactly one versioned `Source Case` as its business truth.
- Human View, Midscene View, Resolved Case and Python Playwright Test are deterministic projections. They carry `source_case_id`, `source_hash`, `dependency_digest`, `build_fingerprint`, generator versions and `do_not_edit=true`.
- Human View uses the step columns `序号`、`操作`、`参数/数据`、`预期结果`; shared account and public data values must show an index or reference path instead of raw secrets.
- Never manually maintain the same case body in multiple formats. Change Source Case or a shared Flow/Page/Component/binding, run plan/sync, and validate the active release. Shared data references belong in Source Case step parameters and are rendered into Human View/Midscene View from that single source.
- A non-`in_sync` active release cannot execute, report, write experience, migrate as active, or complete.

## Storage

- Execution assets: `D:\UI-Test` only.
- Knowledge, experience and redacted evidence indexes: `D:\RAG` only.
- Staging and model exploration output: `D:\UI-Test\_tmp` or a governed run staging path.
- The project must supply `ui-test.project.yaml` v2 with both roots, stable IDs, display names, system/module/function registry, wait strategy and policy references.
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
- Use Draft 2020-12 validation, RFC 8785 canonical hashing, explicit dependency/reverse indexes, immutable releases, expected-active checks and readback validation.
- Formal regression uses only Python + pytest + pytest-playwright. Each test file and node ID must run independently and as part of the suite; filenames must be unique.
- Every formal test gets a fresh BrowserContext and executes the complete login/menu/function Flow. Midscene exploration may use a current-session ready checkpoint route, but a formal Playwright test never skips the full precondition Flow.

## R2 And Results

- R2 approval is current-run, test-environment and visible-UI only. API business writes, production writes and a second submit are blocked.
- A write success followed by verification failure is `write_succeeded_verification_failed`; do not compensate, delete or submit again.
- Teardown releases browser and trace resources only. Created business data is retained with `cleanup_status=not_planned_this_release`.
- Canonical RunResult is the only result truth. Evidence, report, metrics and experience are read-only projections and cannot upgrade status or grant permission.

## Required Gates

Before write: project config v2, Packet v2, Source/IR Schema, migration issue, sensitive scan, Path Plan and `in_sync` checks.

After write/run: scan produced paths and formal references, validate hashes and release status, then produce RunResult and projections. Any stable P0/P1 issue blocks completion.
