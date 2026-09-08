# CR-20260824-002 - Live Release Adapter

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | development-system |
| Change Type | added / repaired / validation / governance |
| Scope | core-skill-md / references-and-assets / scripts-and-validation / safety-and-governance |
| Source | approved public release decision and P1 delivery-gap review |
| Baseline | CR-20260824-001 candidate |
| Author | Codex |
| Related Records | `REQ-CHANGE-DEV-SYSTEM-PUBLICATION-20260824-001` |

## Summary

Add an approval-gated live release adapter and repair deterministic staging for the Development-System lifecycle package.

## Context And Problem

The first candidate stopped at dry-run planning. Its staging script also used a literal wildcard and looked for architecture, development and test documents in the wrong directory. Those defects prevented a reproducible real release.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `scripts/release_adapter.py` | new | Enforce exact approval scope, publish Git, verify remote SHA and independently verify GitBook. |
| `scripts/test_release_adapter.py` | new | Cover path rejection, target matching, remote SHA and GitBook Site state. |
| `references/publish-package-contract.md` | live adapter | Define partial/completed states and credential boundary. |
| `SKILL.md` | references | Require the publish contract before live release work. |
| project `stage_release.ps1` | staging | Enumerate literal source items and use the correct document paths. |

## Decision And Alternatives

Use a fixed Python adapter with argument arrays and an explicit path allowlist. Do not use shell interpolation, force push, implicit repository discovery or a GitHub-success-only completion claim.

## Detailed Change

- Git remote, branch, visibility and each staged root must match the saved approval.
- The adapter stages only approved roots and rejects unrelated staged paths.
- The pushed branch SHA must equal the local commit SHA.
- GitBook content, Space-to-Site linkage and public Site state are independent checks.
- Credentials are read only from the process environment and never written to reports.

## Impact Analysis

The change closes the real-publish P1 gap without changing RC governance or requirement anchors. Public publication remains limited to the two approved repository roots.

## Validation Evidence

| Check | Result |
|---|---|
| Development-System validator | accepted; P0/P1/P2 = 0/0/0 |
| Focused lifecycle and adapter tests | 19 passed |
| Existing runtime/Phase/Story/PH4/CLW tests | passed |
| Sensitive pattern scan | passed after credential-variable hardening |

## Safety And Privacy

No credential values, private materials, RAG governance backups or production data are part of the public package. The adapter cannot create RC or mutate the immutable requirement anchor.

## Risks And Follow-up

GitBook may lag after GitHub push. A timed-out or unlinked Site is reported as `partial` and must not be promoted to completed.
