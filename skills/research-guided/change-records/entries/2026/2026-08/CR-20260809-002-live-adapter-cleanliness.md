# CR-20260809-002 - Live Adapter Cleanliness

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | research |
| Change Type | governance / reference / workflow |
| Scope | core-skill-md / references-and-assets / safety-and-governance / downstream-and-handoff |
| Source | live run feedback and user request |
| Baseline | validated workspace copy from CR-20260809-001 |
| Author | Codex |
| Related Records | CR-20260809-001 |

## Summary

Tighten the research Skill contract so live adapter runs must end with schema-valid structured artifacts, preserve raw malformed feedback separately, and treat flat workspace layouts or malformed packets as repair-needed before completion or deployment.

## Context And Problem

The live Claude run completed useful work, but it left behind malformed raw feedback and an initially flat file layout. That made the run harder to review, harder to validate, and harder to reuse as a clean execution template.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| SKILL.md | Operating Rules, Workflow, Decision Rules | Added live adapter cleanliness and repair-needed handling. |
| references/claude-adapter-contract.md | Output Hygiene | Added required output artifacts and raw/repaired separation. |
| references/severity-and-fallback-rules.md | Live Adapter Cleanliness | Defined malformed feedback and flat layout handling. |
| change-records/* | index and ledgers | Added a new traceable change record. |

## Decision And Alternatives

Chosen: make cleanup and schema validity explicit in the skill contract so future live runs are easier to review.

Alternatives:
- Leave the live run as-is: rejected because it preserves a noisy boundary.
- Modify the executor instead: possible, but outside the current target scope.

## Detailed Change

The updated skill now says live adapter runs must end with schema-valid artifacts. Raw malformed feedback is preserved, repaired in the workspace copy, and validated before any global deployment request. The adapter contract now lists the required artifact set, and the severity rules classify malformed feedback or flat layouts as repair-needed.

## Impact Analysis

- User-facing: live runs are easier to interpret and rerun.
- Skill workflow: adds an explicit cleanup boundary before completion.
- Governance: malformed feedback no longer masquerades as a clean success.

## Validation Evidence

| Check | Command | Result | Evidence |
|---|---|---|---|
| Validation | validate_research_skill.py | pass | Workspace copy validated with change records. |
| Validation | test_research_skill.py | pass | Research skill tests passed. |
| Validation | scan_sensitive.py | pass | No obvious secrets found. |

## Safety And Privacy

No secrets or private content were added. The change only narrows execution hygiene and reviewability.

## Risks And Follow-up

- Need explicit user approval before any global deployment.
- If the global deployment is approved, back up the current global skill first.
