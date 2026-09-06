# Change Records

## Latest Changes

| Date | Change ID | Summary | Status |
|---|---|---|---|
| 2026-09-06 | CR-20260906-005 | Add V2 runtime, artifact-boundary, no-op, junction, CLI, report, and test enforcement. | validated |
| 2026-09-06 | CR-20260906-001 | Document the phase boundary for all routes and downstream skills. | validated |
| 2026-08-29 | CR-20260829-001 | Add grill session schema, formal session gate, failure classification, negative fixtures, and strengthened validator tests. | validated-candidate |

## Category Index

| Category | Path |
|---|---|
| Core Skill Markdown | categories/core-skill-md.md |
| References And Assets | categories/references-and-assets.md |
| Scripts And Validation | categories/scripts-and-validation.md |
| Safety And Governance | categories/safety-and-governance.md |
| Downstream And Handoff | categories/downstream-and-handoff.md |

## Current Residual Risks

- CR-20260829-001's future downstream-schema-reference note is historical; the current candidate's documented writers now reference the V2 contract. Future external consumers still need an explicit compatibility review before adopting it.
- The legacy negative fixtures remain coverage evidence, not a complete V2 behavior proof; final V2 suites and QA evidence cover the candidate scope recorded in CR-20260906-005.
- The failure classification remains a stable contract: any newly added class must never propagate to `completed` without a reviewed schema, validator, and downstream update.
- CR-20260906-005 covers local workflow enforcement only. File-symlink creation was unavailable on this host; actual Windows directory-junction denial passed. It does not claim a global interceptor or semantic inference for external drift.

## Reviewed public documentation

- CR-20260906-007: [reviewed documentation](entries/2026/2026-09/CR-20260906-007-reviewed-public-documentation.md), validated.
- [Current documentation and evidence](https://github.com/Zengxiansheng007/codex-skills/tree/main/_requirements-docs/grill-phase-boundary-20260906).
