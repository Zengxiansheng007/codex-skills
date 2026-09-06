# References And Assets Change Ledger

## Purpose

Track local adapter references that preserve one canonical write-prd contract.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-09-06 | CR-20260906-003 | references/ | added | Add local adapters for shared contracts, Grill return handling, and routing prerequisites. | validated |

## Detailed Records

### CR-20260906-003 - local-prd-contract-adapters

- Section changed: three references adapters.
- Before: The Skill referenced sibling paths that generic package validation could not resolve.
- After: Local adapters point to the canonical write-prd sources without copying or overriding them.
- Validation: Pending final candidate behavior validation; package structure validation to be rerun after this record.
- Detail record: `../entries/2026/2026-09/CR-20260906-003-phase-aware-prd-authoring.md`
