# CR-20260817-006 - CLW PH-3 Worktree, Write-Set And Integration Runtime

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | development-system |
| Change Type | feature / recovery / validation |
| Scope | scripts-and-validation, fixtures |
| Source | CLW PH-3 anchor; FR-CLW3-001 through FR-CLW3-012; AC-CLW3-001 through AC-CLW3-016 |
| Author | Codex bounded takeover after Claude PowerShell approval block |
| Related Records | CR-20260817-001, CR-20260817-005 |

## Summary

Complete the Windows-only Git worktree runtime for isolated Claude slots. The
runtime now records a raw Git `baselineCommit` separately from a canonical
64-character SHA-256 `baselineFingerprint`, computes observed files from Git,
rejects out-of-scope writes, builds hash-bound merge candidates, and performs
Codex-only serial integration in a retained worktree. Merge conflicts, baseline
drift and regression failures fail closed without Agent merge, force reset or
automatic cleanup.

## Root Cause And Takeover

The first live Claude attempt produced valid test-first files but stopped at a
PowerShell approval block and returned `CLAUDE_UNAVAILABLE`. The bounded
preauthorization allowed one same-Story Codex takeover. The original adapter
manifest and feedback remain unchanged; takeover evidence is recorded in the
Story test run.

## Sections Changed

| File | Change Summary |
|---|---|
| `scripts/git_worktree_runtime.py` | Baseline identity split, observed diff/write-set gate, candidate hash validation, Codex integration worktree and merge/recovery gates. |
| `scripts/test_clw_phase3_worktree_runtime.py` | Real Git tests for observed writes, candidate tamper, stable integration, baseline drift, conflict preservation and regression failure. |
| `assets/fixtures/clw-phase3/*` | Positive and negative contract fixtures for slot, write-set and integration behavior. |

## Validation

- `test_clw_phase3_worktree_runtime.py`: `CLW_PHASE3_WORKTREE_RUNTIME_OK`.
- Claude live evidence: visible window and progress captured; adapter status
  `CLAUDE_UNAVAILABLE` due to tool approval, no valid Claude feedback.
- Codex takeover remained within the approved development-system workspace and
  used only temporary Git repositories under the approved runtime root.
- No network, dependency installation, global Skill installation, main
  workspace merge or production write occurred.

## Impact And Rollback

The runtime is additive and does not modify PH-1/PH-2 state or the public
handoff schema. Rollback is limited to this Story's workspace-copy files and
fixtures; original Claude adapter evidence is retained for audit.

## Context And Problem

CLW PH-3 required isolated Windows worktree slots with stable write-set and integration gates. The live Claude attempt reached a PowerShell approval block, so Codex completed the same Story through a bounded takeover.

## Decision And Alternatives

Decision: keep Claude feedback as unavailable evidence and complete the in-scope runtime and tests locally under Codex authority. Alternative rejected: allowing Agent-owned merge or force reset, because integration and completion authority must remain with Codex.

## Impact Analysis

The change adds PH-3 worktree runtime and fixtures without changing PH-1/PH-2 state. Merge conflicts, baseline drift and regression failures now fail closed.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| PH-3 worktree runtime | `python scripts/test_clw_phase3_worktree_runtime.py` | passed | `CLW_PHASE3_WORKTREE_RUNTIME_OK` |

## Safety And Privacy

Work stayed inside the approved workspace and temporary Git runtime roots. No secrets, dependency installation, global Skill installation, network write or production write occurred.

## Risks And Follow-up

Live Agent integration still requires exact approval and valid feedback before it can count as independent Agent completion evidence.
