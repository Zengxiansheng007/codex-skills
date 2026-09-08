# CR-20260810-001 - Strong Research Gate

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | research |
| Change Type | changed / governance / validation |
| Scope | core-skill-md / references-and-assets / scripts-and-validation / safety-and-governance |
| Source | user request |
| Baseline | SHA256 SKILL.md `4C06D0DA7041D66382F62F3223B59E033DFB59A0F12AB630F93CAA0DE08BE193`; test script `FF34B63A02ACA020E564C9B84E02BD0CDC45DFBEE1B389EF94B0671AE9C6E74F`; index `D5531B5489012BBD76130E8467E528558BF2E73D79DD70E94F8818B12D88219D` |
| Author | Codex |
| Related Records | CR-20260809-001, CR-20260809-002 |

## Summary

Make the `research` skill use a strong gate by default on every invocation, and require an explicit user-confirmed downgrade before any light-path research is allowed.

## Context And Problem

The current skill allowed light research to use a lightweight path as part of the normal workflow. The user wants the strong gate to execute every time unless Codex has judged the task simple enough and the user has explicitly approved the downgrade. Without this gate, simple tasks could silently skip the intended Codex-Claude review loop.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| SKILL.md | Description / Operating Rules / Workflow / Decision Rules / References | Added strong default gate and user-confirmed light-path exception. |
| references/strong-gate-and-light-path.md | all | Added dedicated rule reference for the strong gate and the simple-task confirmation flow. |
| scripts/test_research_skill.py | root assertions | Added semantic regression checks for the strong gate and new reference file. |
| change-records/* | index and ledgers | Added a traceable change record for the new behavior. |

## Decision And Alternatives

Chosen: keep the strong gate as the default path and require a user-confirmed downgrade for light research.

Alternatives:
- Keep light research automatic: rejected because it conflicts with the user's new gate requirement.
- Remove light research entirely: possible, but too aggressive; the user only asked for a confirmed downgrade.

## Detailed Change

`SKILL.md` now states that every research invocation starts in strong-gate mode. Light research is only allowed as an explicit exception after Codex judges the task simple enough and the user confirms the downgrade. A new reference file captures the simple-task checklist, recording requirements, and anti-patterns. The test script now asserts that the current skill advertises the strong gate and ships the new reference.

## Impact Analysis

- User-facing: simple tasks no longer silently bypass the gate.
- Workflow: all research starts with Codex planning and an explicit mode decision.
- Testing: the package now has a deterministic regression check for the gate behavior.
- Governance: light-path downgrade is now an approval boundary, not an implicit shortcut.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Baseline capture | `Get-FileHash` on SKILL.md, test script, and index | pass | hashes recorded in this detail record |
| Source review | Read current `SKILL.md`, references, and tests | pass | updated design informed by current package state |
| Workspace validation | `validate_research_skill.py --require-change-records` | pass | accepted-with-constraints, P0/P1/P2 = 0 |
| Workspace tests | `test_research_skill.py` | pass | `ok: research-skill tests passed` |
| Workspace sensitive scan | `scan_sensitive.py` | pass | no findings |
| Global deployment backup | Copy global `research` to `outputs/backups/research-global-before-deploy-20260810-sync/research-<timestamp>` | pass | backup created before sync |
| Global validation | `validate_research_skill.py --require-change-records` on `C:\Users\lenovo\.codex\skills\research` | pass | accepted-with-constraints, P0/P1/P2 = 0 |
| Global tests | `test_research_skill.py` on global skill | pass | `ok: research-skill tests passed` |
| Global sensitive scan | `scan_sensitive.py` on global skill | pass | no findings |

## Safety And Privacy

No secrets, tokens, or private content were added. The only new approval boundary is the user-confirmed light-path downgrade.

## Risks And Follow-up

- Global deployment is complete and validated.
- Future edits should keep the strong-gate semantic test aligned with `SKILL.md`.

Refs:
- Requirement note: outputs/research-skill-strong-gate-2026-08-10/research-skill-strong-gate-requirements.html
- Requirement anchor: outputs/research-skill-strong-gate-2026-08-10/research-skill-strong-gate-requirement-anchor.json
