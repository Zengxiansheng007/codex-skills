# CR-20260820-001 - Write PRD Router Entry

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | development-system |
| Change Type | changed / governance / validation |
| Scope | core-skill-md / references-and-assets / scripts-and-validation / safety-and-governance / downstream-and-handoff |
| Source | user request |
| Baseline | Global skill at `C:\Users\lenovo\.codex\skills\development-system`; workspace candidate at `D:\reference\workspace-candidate\development-system` before deployment validation. |
| Author | Codex |
| Related Records | none |

## Summary

Route PRD, development-plan and test-plan artifact creation from `development-system` to the new `write-prd` top-level router, while preserving `write-requirements-prd` as the downstream PRD-writing child skill.

## Context And Problem

The confirmed Skill topology is `write-prd -> write-requirements-prd -> grill-system`, plus `write-prd -> architecture-design`, `write-prd -> development-plan`, and `write-prd -> test-plan`.

Before this change, `development-system` still named `write-requirements-prd` as the direct route for PRD, development plan, test plan, RTM and acceptance criteria work. That made the new router easy to bypass and could reintroduce artifact mixing or prerequisite ambiguity.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `SKILL.md` | Router Workflow / Routing Map / Required Outputs | Route governed PRD and plan artifacts through `write-prd`; document the child-skill delegation chain. |
| `references/control-plane-and-authority.md` | Independent Skill Boundary | Name `write-prd` as the routed entry point and keep `write-requirements-prd` as a child skill. |
| `references/phase1-boundary-contract.md` | Route Boundary Rules | Route requirements and PRD artifact changes through `write-prd` under `development-system`. |
| `assets/fixtures/router-requirements-to-plan.json` | expectedRoute | Change the expected route from `write-requirements-prd` to `write-prd`. |
| `scripts/validate_development_system.py` | Required terms / change records | Require both `write-prd` and `write-requirements-prd`, and require this detail record. |
| `change-records/index.md` | Latest Changes | Add CR-20260820-001. |
| `change-records/categories/*.md` | Impacted ledgers | Add category entries for core skill, references/assets, scripts/validation, safety/governance and downstream boundary. |
| `change-records/entries/2026/2026-08/CR-20260817-003-clw-st-202-recovery-takeover.md` | Detail record format | Add missing required sections for generic Skill validation. |
| `change-records/entries/2026/2026-08/CR-20260817-005-clw-ph2-aggregate-recovery-test-alignment.md` | Detail record format | Add missing required sections for generic Skill validation. |
| `change-records/entries/2026/2026-08/CR-20260817-006-clw-ph3-worktree-integration.md` | Detail record format | Add missing required sections for generic Skill validation. |
| `change-records/entries/2026/2026-08/CR-20260817-007-clw-ph3-live-integration-and-write-set.md` | Detail record format | Convert legacy prose into the required metadata table and section layout. |

## Decision And Alternatives

Decision: make `write-prd` the only direct PRD/plan artifact route exposed by `development-system`, then let `write-prd` decide whether to call `write-requirements-prd`, `architecture-design`, `development-plan`, or `test-plan`.

Alternative rejected: keep direct `write-requirements-prd` routing in `development-system`. That would preserve the older path but would bypass the new prerequisite, RTM consistency and stale-artifact governance layer.

## Detailed Change

- `development-system` now points PRD, plan, RTM and acceptance criteria creation to `write-prd`.
- The child-skill chain remains explicit so PRD writing still lands in `write-requirements-prd`, and PRD ambiguity still enters `grill-system`.
- The route fixture and validator were updated so the deployed Skill fails validation if the new router entry disappears.
- Legacy detail records that blocked `validate_create_skill.py --require-change-records` were normalized without changing their conclusions.

## Impact Analysis

- PRD requests from `development-system` now pass through the `write-prd` router before detailed PRD writing.
- Existing `write-requirements-prd` behavior is not removed or renamed inside this change.
- Architecture, development plan and test plan routing becomes consistent with the new four-skill PRD system.
- The change is behavior-affecting and global-deploy scoped, so workspace-copy-first, backup and post-deploy validation are required.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Workspace validation | `python scripts/validate_development_system.py` from candidate directory | passed | accepted; P0/P1/P2 = 0/0/0. |
| Global validation | `python scripts/validate_development_system.py` from installed global skill directory | passed | accepted; P0/P1/P2 = 0/0/0 after deployment. |
| Sensitive-data scan | Built into `validate_development_system.py` and generic Skill validator | passed | no secret-pattern findings. |
| Route evidence | Inspect `SKILL.md`, route fixture and required validator terms | applied | `write-prd` is required; `write-requirements-prd` remains required as child skill evidence. |
| Generic Skill validation | `python validate_create_skill.py <skill-folder> --require-change-records` | passed | accepted-with-constraints; P0/P1/P2 = 0/0/0 in workspace and global install. |

## Safety And Privacy

No credentials, tokens, cookies, private keys or production-only details are added. Global deployment requires an approved deployment boundary, backup of the current global Skill, and post-deploy validation.

## Risks And Follow-up

- Keep the backup path in the final task report for rollback readiness.
- Any future direct PRD route added to `development-system` must preserve the `write-prd` router entry unless a new confirmed requirement supersedes this topology.

Refs:

- `SKILL.md`
- `references/control-plane-and-authority.md`
- `references/phase1-boundary-contract.md`
- `assets/fixtures/router-requirements-to-plan.json`
- `scripts/validate_development_system.py`
