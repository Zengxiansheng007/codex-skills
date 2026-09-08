# CLW PH-3 Windows Isolated Concurrency Contract

This contract is scoped to `CLW-PH-3`. It extends the PH-2 serial Story runtime without weakening any PH-1/PH-2 gate.

## Entry Gate

PH-3 implementation and live acceptance require PH-2 completion. Static contract preparation and temporary-repository tests do not satisfy that gate.

## Slot Isolation

- Codex alone creates, locks, repairs, merges and removes worktrees and branches.
- Each slot has unique Story, Agent, worktree, branch, workspace/baseline fingerprint, permission policy, declared write set, event chain and evidence set.
- Initial acceptance is Windows, a Git repository without submodules, and at most two slots.
- A worktree failure fails closed. There is no automatic sandbox fallback and no `git switch -B` or equivalent branch reset.

## Scheduling And Write Sets

- Only dependency-complete Stories with explicit `parallelEligible=true` can run concurrently.
- Normalize Windows paths case-insensitively. Empty, wildcard, escape, duplicate and parent/child-overlapping write sets are rejected.
- Compare observed changed files from the recorded baseline with the declaration. Any out-of-scope write routes to requirements review.

## Integration

- A merge candidate is immutable and hash-bound to Story/FR/AC, base/head, diff, declared/observed paths, feedback validation, tests and evidence.
- Integrate in a separate worktree using stable dependency/Story order. Baseline drift, conflict, failed regression, missing evidence or unmapped actions stops integration.
- Do not invoke an Agent to resolve conflicts automatically. Dirty or failed worktrees are preserved until an explicit cleanup decision.

Trace: FR-CLW3-001 through FR-CLW3-012; AC-CLW3-001 through AC-CLW3-016.
