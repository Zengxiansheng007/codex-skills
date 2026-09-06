# CR-20260906-007 - Reviewed public documentation

| Field | Value |
| --- | --- |
| Status | validated |
| Target Skill | grill-system |
| Change Type | documentation / evidence clarification |
| Scope | references-and-assets / core-skill-md |
| Source | User request to review, adjust and publish the task documentation |
| Baseline | Code release b4fa50611f2f4c627903df2cc439ff483ce6cfc6; runtime code unchanged |
| Author | Codex |

## Summary

Clarify current release documentation and distinguish historical preparation notes from completed validation.

## Context And Problem

Planning snapshots still described work as pending after implementation and publication. Some category notes also retained their initial pending wording beside validated release records.

## Sections Changed

| File | Section | Change Summary |
| --- | --- | --- |
| change-records/categories | Validation projection | Preserve initial notes as historical; link current completed evidence |
| change-records/index.md | Current documentation | Add this documentation revision and public documentation pointer |
| SKILL.md | Formal Session Gate | Include validate in the 17-command inventory; separate V2 contract from legacy V1 inspection |
| references/phase-boundary-contract.md | Digest input | Specify lowercase expectedSha256 to match actual exact-string comparison |

## Decision And Alternatives

Publish a versioned current-state documentation set rather than overwrite immutable planning/test records. The release's implemented behavior and approved requirements remain unchanged.

## Impact Analysis

Markdown-only changes. No runtime Python, JSON Schema, fixture, installed dependencies, or business rules changed.

## Validation Evidence

Documentation link, identifier, CLI-inventory, evidence-count, privacy and package-structure checks passed before publishing. Raw task/model/audit logs and machine paths are not published. Existing code test evidence is reused because executable content is unchanged.

## Safety And Privacy

Only the reviewed public documentation and these Markdown corrections are in the release scope. Historical raw evidence and global backup details remain local.

## Risks And Follow-up

The file-symlink host capability skip and local-only guard boundary remain explicit. [Current public documentation](https://github.com/Zengxiansheng007/codex-skills/tree/main/_requirements-docs/grill-phase-boundary-20260906) provides the updated evidence projection.
