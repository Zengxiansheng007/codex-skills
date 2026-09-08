# CR-20260817-007 - CLW PH-3 Live Integration And Write-Set

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | development-system |
| Change Type | feature / validation |
| Scope | scripts-and-validation |
| Source | CLW PH-3 live integration gate |
| Baseline | Workspace after CR-20260817-006 |
| Author | Codex |
| Related Records | CR-20260817-006 |

## Summary

Add a reproducible Codex-owned PH-3 live integration harness and repair observed write-set collection for untracked nested files.

## Context And Problem

The PH-3 live gate requires two independent Claude slots, declared and observed write-set validation, candidate hashing, Codex-only commits, stable integration merge and regression evidence. During live integration, Git reported an untracked directory as `live` instead of the created file `live/a.txt`, causing a false out-of-scope write-set rejection.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `scripts/git_worktree_runtime.py` | Observed write-set collection | Expand untracked directories via `git status --untracked-files=all`. |
| `scripts/test_clw_phase3_worktree_runtime.py` | PH-3 regression coverage | Verify nested untracked file handling and integration behavior. |
| `scripts/build_clw_ph3_live_packets.py` | Live packet generation | Preserve `feedbackSchema` exactly from the active preauthorization policy. |
| `scripts/run_clw_ph3_live_integration.py` | Live integration harness | Commit accepted slots, build hash-bound candidates, integrate in a Codex-owned worktree and run regression checks. |

## Decision And Alternatives

Decision: keep integration Codex-owned and repair observed write-set collection to report nested untracked files precisely. Alternative rejected: broadening declared write sets to directory-level paths, because that would weaken merge safety.

## Detailed Change

- Live packet generation preserves `feedbackSchema` exactly from the active preauthorization policy.
- Observed write-set collection expands untracked directories via `git status --untracked-files=all`.
- `run_clw_ph3_live_integration.py` commits each accepted slot, builds hash-bound candidates, integrates in a separate Codex-owned worktree and runs a regression check.

## Impact Analysis

Nested untracked files are now attributed precisely, reducing false write-set rejections while preserving out-of-scope write detection. The change affects PH-3 integration tooling and tests only.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| PH-3 worktree runtime | `python scripts/test_clw_phase3_worktree_runtime.py` | passed | `CLW_PHASE3_WORKTREE_RUNTIME_OK` |
| PH-3 live integration | `python scripts/run_clw_ph3_live_integration.py` | passed | `CLW_PHASE3_LIVE_INTEGRATION_OK` |
| PH-3 post-live A/B gates | review of live gate output | passed | `accepted` |

## Safety And Privacy

The harness uses local worktrees and does not add secrets, dependency installation, global Skill writes, production writes or external publication.

## Risks And Follow-up

Future PH-3 live packets must preserve exact policy schema and keep Codex-owned integration separate from Agent execution slots.
