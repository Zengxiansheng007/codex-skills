# CR-20260824-003 - Default Publish Targets

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | development-system |
| Change Type | behavior / validation / governance |
| Scope | references-and-assets / scripts-and-validation / safety-and-governance |
| Source | user-confirmed default GitHub repository and GitBook Site/Space |
| Baseline | CR-20260824-002 validated global Skill |
| Author | Codex |
| Related Records | `REQ-DEV-SYSTEM-RAG-PUBLISH-20260824-001` |

## Summary

Make the public `codex-skills` GitHub repository and the confirmed GitBook Site/Space the default release targets while preserving exact approval gates and explicit overrides.

## Context And Problem

The live adapter required callers to repeat every remote identifier. That increased operator error and allowed the GitBook target to be supplied without being represented in the approval object.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `scripts/release_adapter.py` | defaults and approval validation | Add stable default target IDs and fail closed when GitBook approval fields do not match. |
| `scripts/test_release_adapter.py` | regression coverage | Verify defaults and reject a mismatched GitBook Site. |
| `references/publish-package-contract.md` | default target binding | Document defaults, override behavior and the non-authoritative nature of `~/changes/<number>/` URLs. |
| `change-records/index.md` | latest changes | Register this candidate change. |

## Decision And Alternatives

Use stable repository, organization, Site and Space identifiers. Do not store a GitBook draft/revision URL as the target, and do not treat defaults as approval.

## Detailed Change

- `--repository`, `--branch`, `--organization-id`, `--gitbook-site-id` and `--gitbook-space-id` now have stable defaults.
- Explicit overrides remain available.
- `validate_approval` now compares the GitBook organization, Site and Space with approval fields before any GitHub write.
- The GitBook change-view URL is normalized to stable IDs and is not persisted as an operational target.

## Impact Analysis

Future release commands may omit remote target arguments, reducing target-selection mistakes. Existing callers that provide explicit targets remain supported. Approval files must now include the exact GitBook organization, Site and Space, which intentionally fails closed for older incomplete approvals.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Global baseline | Development-System validator and adapter tests | passed | P0/P1/P2 = 0/0/0; 8/8 tests |
| Target binding | GitBook read-only API verification | passed | Site is public/published; target Space is the only linked Space |
| Focused workspace tests | `test_release_adapter.py` | passed | 10/10 tests |
| Full workspace regression | all `scripts/test_*.py` | passed | 13/13 scripts |
| Workspace validator | `validate_development_system.py` | passed | accepted; P0/P1/P2 = 0/0/0 |
| Sensitive-data scan | token-pattern scan | passed | 0 matching files |
| Global deployment | approved backup and controlled installation | passed | backup `development-system-backup-20260824-default-targets` |
| Global full regression | all `scripts/test_*.py` | passed | 13/13 scripts; adapter 10/10 |
| Global validators | specialized plus generic Skill validators | passed | P0/P1/P2 = 0/0/0 |
| Candidate/global parity | relative-path SHA-256 comparison | passed | 215/215 files; 0 differences |

## Safety And Privacy

No credential values are stored. `GITHUB_TOKEN` and `GITBOOK_TOKEN` remain environment-only. Defaults never authorize a publish, path, visibility or RC transition.

## Risks And Follow-up

The candidate must pass focused and full regression, sensitive-data scanning, explicit installation approval, backup, global deployment and post-install validation before this record becomes `validated`.
