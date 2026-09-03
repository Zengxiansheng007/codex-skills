# CR-20260902-002 - Formal V2 Execution Readiness

| Field | Value |
|---|---|
| Status | proposed |
| Target Skill | ui-test workspace candidate |
| Change Type | fixed / validation / governance |
| Scope | scripts-and-validation / safety-and-governance |
| Source | user-approved global install, formal migration and real UI/R2 gate |
| Baseline | CR-20260902-001 validated candidate |
| Author | Codex |
| Related Records | AUTH-UI-TEST-REPAIR-20260902-DEPLOY |

## Summary

Close the gap between the offline candidate and a formally collectible, marker-bound, current-run R2 execution package.

## Context And Problem

The v2 generated Python was syntactically valid but lacked pytest risk and identity markers. The project adapter also needed a formal runtime bridge that loads governed values without persisting credentials and rejects offline fixtures during deployment.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `scripts/ui_test_core/compiler_v2.py` | Playwright renderer | Generate P0/UI/R2 and case/branch markers. |
| project adapter runtime/deployer | formal execution | Bind Guard, R2, sequence, result/evidence and rollback boundaries. |
| tests | live readiness | Validate marker collection and no-write failure paths. |

## Decision And Alternatives

Keep formal pytest identity in generated files rather than relying on manually maintained wrapper tests. Load actual Runtime and credentials only during formal compile/run; offline fixtures are rejected for formal output.

## Detailed Change

Pending implementation and validation.

## Impact Analysis

New formal v2 tests become collectible by existing pytest configuration and remain fail-closed before BrowserContext or submission when identity, approval or data gates fail.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Focused and full regression | pending | pending | candidate evidence |
| Sensitive scan | pending | pending | candidate evidence |
| Formal preflight | pending | pending | deployment evidence |

## Safety And Privacy

Credential values remain memory-only. Offline Runtime fixtures must never be published to formal D-drive releases.

## Risks And Follow-up

Real UI outcome remains unknown until the separately approved A/B runs finish with canonical evidence.

Refs: RA-UI-TEST-REPAIR-20260830@v0.5; CR-20260902-001.
