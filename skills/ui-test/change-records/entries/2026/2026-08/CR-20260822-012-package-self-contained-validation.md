# CR-20260822-012 - Package Self-Contained Validation

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | ui-test |
| Change Type | fixed / packaging / validation |
| Scope | registry validation, package fixtures, global installation |
| Source | post-install validation finding |
| Baseline | CR-20260822-011 |
| Author | Codex |

## Summary

Removed the installed-package dependency on the workspace-only `source-baseline.json` while preserving full workspace baseline validation when that file is available.

## Root Cause

The registry validator tests resolved their baseline only from the parent of the Skill directory. That path exists in the development workspace but is not part of a globally installed Skill package.

## Repair

- Added `assets/source-baseline.json` as a package-local fallback.
- Updated tests to prefer the workspace baseline and otherwise use the package fallback.
- Updated relative source resolution so package-local baseline entries resolve relative to the baseline file.
- Kept absolute workspace source paths supported for the full cross-Skill baseline.

## Validation

- Candidate suite passes after repair: 99 tests.
- Global package suite passes after reinstall: 99 tests.
- Package-local baseline validates without `C:\Users\lenovo\.codex\source-baseline.json`.
- Sensitive scan remains clear.

## Installation Evidence

- Pre-install backup: `C:\Users\lenovo\Documents\Codex\global-install-backups\ui-test-asset-governance-20260822\ui-test-preinstall-20260822-201448`
- Initial install evidence: `evidence/PH-06/PH06-ST02/EVD-PH06-ST02-ui-test-global-install-20260822.json`
- Final repaired-package backup: `C:\Users\lenovo\Documents\Codex\global-install-backups\ui-test-asset-governance-20260822\ui-test-preinstall-20260822-204154`
- Final install evidence: `evidence/PH-06/PH06-ST02/EVD-PH06-ST02-ui-test-global-install-20260822.json`
- Final candidate/global package tree hash: `sha256:3041ad8c02252d6a9876318c4184e0bfee823b1aa50681a0d2f2791f0f16bcb2`

## Context And Problem

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.

## Sections Changed

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.

## Decision And Alternatives

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.

## Impact Analysis

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.

## Validation Evidence

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.

## Safety And Privacy

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.

## Risks And Follow-up

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.
