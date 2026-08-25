# CR-20260822-001 - UI-Test Asset Governance

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | ui-test-checkpoint-runtime |
| Change Type | changed / validation / governance |
| Scope | scripts-and-validation / safety-and-governance |
| Source | approved UI-Test asset-governance requirements |
| Baseline | workspace-copy-first; current SKILL checksum sha256:262fa6157d4fab97562e5454e836de0c227c3dba092721d33850a46dbbdb5009; global copy unchanged |
| Author | Codex |
| Related Records | ui-test/CR-20260822-007 |

## Summary

Fix redacted public host assertions and verify two fresh live-public sessions.

## Context And Problem

The candidate family required consistent ownership, validation, privacy, runtime and retirement boundaries before global installation.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `SKILL.md` and/or bundled resources | scripts-and-validation / safety-and-governance | Fix redacted public host assertions and verify two fresh live-public sessions. |

## Decision And Alternatives

Keep one normative `ui-test` control plane and small purpose-specific child Skills. Do not preserve duplicate ownership or bypass current validation rules.

## Detailed Change

The change is bounded to the workspace candidate and follows the approved D-drive asset, canonical result, R2 approval and compatibility-retirement contracts where applicable.

## Impact Analysis

Existing global Skills remain unchanged. Consumers gain explicit deterministic validation and fail-closed safety behavior after a separately authorized installation.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Skill quality | `validate_create_skill.py --require-change-records` | validated | candidate validation evidence |
| Behavior | bundled tests and public forward test where applicable | passed | PH-06 evidence |
| Sensitive data | candidate package scan | clear | PH-06 evidence |

## Safety And Privacy

No credential, private raw URL, Cookie, Token, browser state, or production data is added. This record grants no execution or installation permission.

## Risks And Follow-up

Private P0-A/P0-B live evidence and global installation remain pending separate external gates.

Refs: RA-UI-TEST-ASSET-GOV-20260822-v1.0
