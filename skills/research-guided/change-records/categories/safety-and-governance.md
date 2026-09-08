# Safety And Governance Change Ledger

## Purpose

Record changes to approval gates, sensitive-data handling, or governance rules.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-08-25 | CR-20260825-001 | failure classification / plan mode block | governance | Add stable failure classes and plan mode rejection for live research. | validated |
| 2026-08-21 | CR-20260821-001 | Claude research approval / MCP allowlist | governance | Self-approve public Claude retrieval with Exa/Firecrawl MCP tools while preserving private/restricted-source blockers. | validated |
| 2026-08-10 | CR-20260810-001 | research light-path downgrade | governance | Require user confirmation before using any light-path downgrade. | validated |
| 2026-08-09 | CR-20260809-002 | approval gates / live adapter hygiene | updated | Clarify repair-needed handling for malformed live adapter output. | validated |
| 2026-08-09 | CR-20260809-001 | Rules | governance | Add severity, fallback, sensitive boundary. | validated |
## Detailed Records

### CR-20260825-001 - research-repair-governance

- Section changed: Safety and governance rules for plan mode, failure classification, and fail-closed conditions.
- Before: No plan mode rejection, no stable failure classes, no preflight or result validation.
- After: Plan mode is explicitly blocked; 16 stable failure classes with severity and propagation; preflight and result validation enforce all fail-closed conditions.
- Why: Live research stalled in plan mode, lost MCP visibility, reused stale sessions, and accepted unverified output.
- Impact: Stronger stop conditions for live research execution.
- Validation: Pending execution due to tool permission restriction.
- Detail record: ../entries/2026/2026-08/CR-20260825-001-research-repair.md

### CR-20260821-001 - auto-approved-mcp-research

- Section changed: Claude live research approval and MCP tool permission boundary.
- Before: The skill did not explicitly allow Codex to approve Claude MCP retrieval tools without another user prompt.
- After: Codex may self-approve only public Claude research calls and the explicit Exa/Firecrawl MCP allowlist.
- Why: The user wants unattended Claude retrieval when Codex needs research evidence.
- Impact: Faster research loop; reduced approval friction; no expansion to private, paid, login-gated, write, install, or shell actions.
- Validation: Workspace and deployed validation passed; sensitive scan passed.
- Detail record: ../entries/2026/2026-08/CR-20260821-001-auto-approved-mcp-research.md

### CR-20260810-001 - light-path-confirmation

- Section changed: research light-path downgrade approval boundary.
- Before: light research could be used as a lightweight path without an explicit user-confirmed downgrade step.
- After: the skill must ask the user before any light-path downgrade, and no silent downgrade is allowed.
- Why: The user explicitly wants the strong gate to execute on every research call unless a simple-case exception is confirmed.
- Impact: Low-risk research can still be optimized, but only with explicit approval.
- Validation: Pending.
- Detail record: ../entries/2026/2026-08/CR-20260810-001-strong-research-gate.md

### CR-20260809-002 - live-adapter-cleanliness

- Section changed: governance rules for live adapter completion and repair handling.
- Before: Malformed output was not explicitly distinguished from recoverable format debt.
- After: Malformed feedback packets and flat layouts must be treated as repair-needed before completion or deployment.
- Why: This prevents a noisy live run from being misread as a clean success.
- Impact: Stronger stop conditions for live execution and deployment decisions.
- Validation: Workspace validation passed.
- Detail record: ../entries/2026/2026-08/CR-20260809-002-live-adapter-cleanliness.md

### CR-20260809-001 - safety-rules

- Section changed: Operating Rules, Decision Rules, severity-and-fallback-rules.
- Before: No severity rules or fallback policy.
- After: P0/P1/P2 rules, blocked-by-default, sensitive content boundary.
- Why: PRD requires traceable severity handling and privacy-by-default.
- Validation: Rules documented.
- Detail record: ../entries/2026/2026-08/CR-20260809-001-claude-research-loop.md

### CR-20260908-002 - Research routing split

- Section changed: approved candidate routing/identity boundary.
- Before: generic research was the Claude execution entry.
- After: generic router and retained guided execution are separate.
- Why: approved research-routing review.
- Impact: research-guided; no global writes.
- Validation: candidate evidence in development workspace; initially pending.
- Detail record: [record](../entries/2026/2026-09/CR-20260908-002-research-routing.md).
