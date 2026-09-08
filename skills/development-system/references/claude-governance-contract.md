# Claude External-Agent Governance Contract

## Ownership

Codex owns policy evaluation, approval, state transitions, requirement drift review, and completion. Claude is a registered execution Agent and cannot authorize itself or mark Development System complete.

## Registry

Each Claude profile has one `agentId`, one `adapterId`, a version, capabilities, availability, a feedback schema reference, and `completionAuthorityIsolated=true`. Duplicate identity or adapter ownership fails closed.

## Preauthorization Lifecycle

An executable policy is task-scoped, versioned, hash-bound, time-bounded, active, and non-reusable across projects. The policy hash is SHA-256 over the canonical policy with `policyHash` omitted. Empty network access is valid; wildcard workspace, action, tool, data, network, or stop-condition boundaries are forbidden.

Automatic approval requires the request to carry the matching `policyId`, computed `policyHash`, packet hash, workspace, actions, tools, data, network, credential boundary, feedback schema, timeout, rounds, concurrency, and stop conditions. Missing, expired, revoked, tampered, or enlarged boundaries fail closed.

## Dry-Run Gate

The first packet/policy pair must have a hashed dry-run manifest with `mode=dry-run`, `status=DRY_RUN_OK`, `spawnedProcess=false`, the exact packet and policy hashes, and a valid timestamp inside the policy lifetime. A plain status string is not approval evidence.

## Status Projection

Machine codes remain stable. User-facing output adds a Chinese label and never replaces the machine code. Unknown states map to `failed` / `失败`.

## Bounded Takeover

Codex may take over only after Claude is unavailable, times out, or reaches the configured consecutive-invalid-feedback threshold. The cycle, Story, authorization fingerprint, round, and evidence lineage must match the failed attempt. One active policy defines the round and takeover budgets. Cross-cycle, cross-Story, changed-boundary, evidence-free, and over-budget takeover attempts fail closed.

## Manual Gates

Installation, global writes, production writes, publish, delete, permission changes, external messages, credential export, and new boundaries always require separate user approval.
