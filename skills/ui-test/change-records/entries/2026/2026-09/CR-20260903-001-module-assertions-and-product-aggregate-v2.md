# CR-20260903-001 - Module Assertions And Product Aggregate V2

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | ui-test workspace candidate |
| Change Type | contract / compiler / renderer / validation / deployment |
| Scope | core-skill-md / references-and-assets / scripts-and-validation / safety-and-governance |
| Source | user-approved total-test-case and per-module assertion repair plan |
| Baseline | installed ui-test plus Tianjin A/B active on 2026-09-03 |
| Author | Codex |

## Summary

Restore page-module-level P0 semantics across every projection and replace concatenated product Human Views with a strict recursive v2 aggregate.

## Context And Problem

The first v2 migration collapsed A/B page behavior into one composite feature step and removed explicit assertion references. The formal Tianjin deployer then joined two Human View files, so the product root lost the project/product/system/module/function hierarchy even though the generated file remained hash-consistent.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `SKILL.md`, `references/asset-governance.md` | project governance | Require registry-backed module coverage, immediate postconditions and two-phase formal activation. |
| `schemas/*.json` | v2 contracts | Add module registry, recursive product outline, strict aggregate manifest and no-submit qualification result. |
| `scripts/ui_test_core/compiler_v2.py` | compile gates | Generate one shared step/assertion model and reject missing, composite or unregistered coverage. |
| `scripts/ui_test_core/product_aggregate.py` | product projection | Render the full recursive hierarchy and shared prerequisites once. |
| `scripts/ui_test_core/case_sync.py` | release lifecycle | Separate immutable successor preparation from CAS activation. |
| tests | regression | Add negative Schema gates, projection/aggregate Golden checks and no-submit qualification behavior. |

## Decision And Alternatives

Use a registry-backed compiler gate and IR-driven recursive renderer. Retaining the Human View join was rejected because it cannot preserve product hierarchy or prove assertion identity; allowing direct activation was rejected because it would expose an unqualified semantic successor.

## Impact Analysis

All semantic changes produce new immutable A/B builds. Existing releases and RunResults remain audit-only and unchanged. New builds are not eligible for activation until both matching qualification results prove zero submission and zero sequence allocation.

## Validation Evidence

| Check | Result |
|---|---|
| Full candidate suite | 273 passed |
| Installed global Skill suite | 243 passed |
| Formal A/B no-submit qualification | A 12 steps passed; B 13 steps passed; both zero submit and zero sequence allocation |
| Formal verifier | valid/in_sync/ready; 336 historical files unchanged |
| GitHub public verification | pending publication |

## Safety And Privacy

Credentials remain references or process-memory values. The public package excludes Tianjin locators, private URLs, credentials and browser screenshots. Qualification must stop before the submit operation.

## Risks And Follow-up

This record closes only the aggregate/assertion specialty. Existing diagnostics, orphan-run, Runtime classification and independent-completion defects remain separate `repair-needed` items.
