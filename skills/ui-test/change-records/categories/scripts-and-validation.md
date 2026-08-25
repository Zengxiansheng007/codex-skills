# Scripts And Validation Change Ledger

## Purpose

Track deterministic runtime, compiler, validator and test changes.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-08-18 | CR-20260818-001 | scripts/ui_test_core and tests | added | Add standard-library validator and contract tests | applied |
| 2026-08-22 | CR-20260822-001 | scripts/ui_test_core/registry_validator and tests | added | Add contract registry and source baseline validator with lifecycle state support | applied |
| 2026-08-22 | CR-20260822-002 | schemas, scripts/ui_test_core/case_contracts and tests | added | Add Source Case and IR contracts with RFC 8785 canonical hashing | applied |
| 2026-08-22 | CR-20260822-003 | project config schema/loader, Path Planner and tests | added | Enforce v2 write config, asset-type roots, business hierarchy and Windows containment | applied |
| 2026-08-22 | CR-20260822-004 | Packet v2 schema/validator, migration adapter and tests | changed | Centralize legacy adaptation and machine-readable fail-closed issues | applied |
| 2026-08-22 | CR-20260822-005 | preflight/post-write gate, sensitive scanner and tests | added | Block invalid config, contract, path, secret, migration and release states | applied |
| 2026-08-22 | CR-20260822-007 | private pilot templates and candidate validation | fixed | Add R2 runtime tests, exact-host guard and current validator compatibility | validated |
| 2026-08-22 | CR-20260822-008 | pilot pytest config and sensitive-scan fixture | fixed | Register governed markers and distinguish explicit environment references from secret values | validated |
| 2026-08-22 | CR-20260822-009 | CompletionEvaluator migration status | fixed | Preserve failed versus deferred migration semantics with boolean compatibility | validated |
| 2026-08-25 | CR-20260825-001 | scripts/ui_test_core/semantic_rules and tests | added | Add Semantic Rule Registry, stable Issue List, pre-lowering validation and parameter atomization | validated |
| 2026-08-25 | CR-20260825-002 | product aggregate, JCS wrapper, semantic rules and tests | added | Add product Markdown/outline projection, P0 joint coverage, RFC 8785 dependency gate and A/B semantic repair coverage | validated |
| 2026-08-25 | CR-20260825-003 | runtime dependency metadata | changed | Install pytest 9.1.1, lock the dependency and validate the full pytest suite | validated |

## Detailed Records

### CR-20260822-007 - candidate-validation-and-pilot-runtime

- Section changed: private pilot generator, runner and validation fixtures.
- Before: no generated Approval Record or canonical failure result.
- After: generated runtime persists redacted approval and RunResult evidence.
- Why: PH-05 exit requirements and final package validation.
- Impact: private network failures remain zero-submit and machine-readable.
- Validation: 99 tests plus warning-free two-case pytest collection.
- Detail record: `../entries/2026/2026-08/CR-20260822-007-candidate-validation-and-pilot-runtime.md`.

### CR-20260822-008 - pytest-marker-and-env-reference-governance

- Section changed: pilot pytest configuration, private runner metadata and sensitive scan tests.
- Before: manual collection emitted unknown-marker warnings and a password environment-variable name resembled a literal credential assignment.
- After: five governed markers are registered and runtime value mappings use an explicit `env_ref` object.
- Why: keep manual pytest execution warning-free without weakening secret detection.
- Impact: generated and current pilot assets share one marker contract; real credential literals remain blocked.
- Validation: 101 tests, warning-free two-case collection and dual-scope sensitive scan.
- Detail record: `../entries/2026/2026-08/CR-20260822-008-pytest-marker-and-env-reference-governance.md`.

### CR-20260822-009 - deferred-migration-completion-status

- Section changed: CompletionEvaluator and final governance evidence builder.
- Before: every non-passed migration state emitted `migration-failed`.
- After: governed `passed`, `failed` and `deferred` states emit precise blockers while legacy booleans remain supported.
- Why: the first-pilot migration dry-run passed, but historical disposition is deferred until private validation completes.
- Impact: completion remains blocked with accurate machine-readable semantics.
- Validation: completion compatibility and deferred-state regression tests.
- Detail record: `../entries/2026/2026-08/CR-20260822-009-deferred-migration-completion-status.md`.
