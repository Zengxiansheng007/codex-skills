# CR-20260809-001 - Development System Local Global Loop

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | development-system |
| Change Type | governance / validation |
| Scope | core-skill-md / references-and-assets / scripts-and-validation / safety-and-governance |
| Source | user request and real-use retrospective findings |
| Baseline | `development-system` validator accepted before changes; prior retrospective identified DS-RETRO-001 as P1 and related P2 gaps |
| Author | Codex |
| Related Records | none |

## Summary

Add repeatable guidance and validation coverage for local direct implementation, global Skill edit deployment, compact requirement anchors, and system-use retrospectives.

## Context And Problem

A real `create-skill` development run showed that `development-system` worked as a top-level router, but several details depended on judgment rather than explicit skill instructions. The most important gap was the missing safe pattern for changing global Codex Skills through a workspace copy, approval-gated deployment, and deployed validation.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `SKILL.md` | Router Workflow | Added local direct loop selection and global Skill edit workflow routing. |
| `SKILL.md` | Required Outputs | Added local implementation evidence and system-use retrospective output. |
| `SKILL.md` | References | Added direct links to new references. |
| `references/router-contract.md` | Title | Renamed title from old system name to Development System. |
| `references/requirement-anchor-template.md` | all | Added minimum and complete anchor templates. |
| `references/local-direct-implementation-loop.md` | all | Added local Codex implementation loop and completion rules. |
| `references/local-global-skill-edit-loop.md` | all | Added workspace-copy, approval, backup, deploy, and revalidate flow. |
| `references/system-use-retrospective.md` | all | Added retrospective sections and severity guide. |
| `assets/fixtures/router-local-global-skill-edit.json` | all | Added route fixture for global Skill edit scenario. |
| `scripts/validate_development_system.py` | required files and checks | Added coverage for new references, fixture, change records, title, and Change ID. |
| `scripts/validate_handoff_codex_system.py` | required files | Added package-level coverage for new references, fixture, and change records. |
| `change-records/` | all | Added traceable record system for this update. |

## Decision And Alternatives

Chosen: keep `SKILL.md` as a concise router and put detailed local/global edit, local direct implementation, anchor, and retrospective rules in separate references.

Alternatives considered:

- Put all new rules into `SKILL.md`: rejected because it would bloat the top-level router.
- Treat local direct implementation as just a variant of the A2A loop: rejected because local work does not produce adapter feedback packets and needs different evidence.
- Skip change records because `development-system` did not previously require them: rejected because the new `create-skill` contract applies to existing Skill updates.

## Detailed Change

The router now explicitly chooses between local direct implementation and A2A adapter execution. Global Codex Skill edits must follow the workspace-copy pattern: read global, edit workspace, validate workspace, ask for deployment approval, back up global when practical, deploy, and revalidate global. A compact requirement anchor template is available for complex tasks, and a system-use retrospective reference explains how to evaluate the router after real development runs.

## Impact Analysis

- Future `development-system` tasks have less ambiguity when Codex implements locally.
- Global Skill edits have stronger approval and validation evidence.
- Retrospectives become a documented output rather than a user-specific convention.
- Validators now catch missing new references and stale title drift.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Source development-system validator | `python -B skills/development-system/scripts/validate_development_system.py skills/development-system` | passed | accepted, P0/P1/P2 = 0 |
| Package-level validator | `python -B scripts/validate_handoff_codex_system.py <system-root>` | passed | accepted, P0/P1/P2 = 0 |
| Global deployment | approval-gated copy from source to `C:\Users\lenovo\.codex\skills\development-system` | passed | completed after source validation |
| Global development-system validator | `python -B validate_development_system.py <global development-system>` | passed | accepted, P0/P1/P2 = 0 |
| Sensitive scan | validator sensitive-pattern scan | passed on source validation | no P0 secret-pattern finding |

## Safety And Privacy

No secrets are intentionally included. Local paths are used only as same-machine development evidence. Global Skill deployment must remain approval-gated.

## Risks And Follow-up

- No P0/P1 risk remains open after source and deployed global validation.
- Future packaging or WorkBuddy migration was not in scope for this repair.

Refs:

- Real-use retrospective: `C:\Users\lenovo\Documents\Codex\2026-08-09\new-chat-2\outputs\development-system-current-dialogue-2026-08-09\development-system-real-use-retrospective-2026-08-09.md`
- Current source root: `C:\Users\lenovo\Documents\Codex\2026-07-15\fen\work\handoff-system-codex-v1\skills\development-system`
