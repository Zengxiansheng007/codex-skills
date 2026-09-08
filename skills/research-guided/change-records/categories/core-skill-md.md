# Core SKILL.md Change Ledger

## Purpose

Record changes to `SKILL.md` workflow, operating rules, validation, and delivery contract.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-08-25 | CR-20260825-001 | SKILL.md | governance | Add FR-RR-001 through FR-RR-006 operating rules and validation commands for research repair. | validated |
| 2026-08-21 | CR-20260821-001 | SKILL.md | governance | Add Codex self-approval for Claude public research calls and the approved MCP retrieval allowlist. | validated |
| 2026-08-10 | CR-20260810-001 | SKILL.md | updated | Default all research to strong gate and gate light-path downgrade on user confirmation. | validated |
| 2026-08-09 | CR-20260809-002 | Operating Rules, Workflow, Decision Rules | updated | Tighten live adapter output hygiene and repair handling. | validated |
| 2026-08-09 | CR-20260809-001 | All | added | Implement Codex-Claude two-round research loop. | validated |
## Detailed Records

### CR-20260825-001 - research-repair

- Section changed: SKILL.md Operating Rules and Validation.
- Before: SKILL.md did not enforce plan mode rejection, tool registry, preflight, result schema validation, format/reinforcement bounds, or failure classification.
- After: SKILL.md enforces all six FR-RR rules and references the new scripts and schemas.
- Why: Live research stalled in plan mode, lost MCP visibility, reused stale sessions, and accepted unverified output.
- Impact: Future live research runs have deterministic fail-closed gates for all known failure modes.
- Validation: Pending execution due to tool permission restriction.
- Detail record: ../entries/2026/2026-08/CR-20260825-001-research-repair.md

### CR-20260821-001 - auto-approved-mcp-research

- Section changed: SKILL.md Operating Rules, Workflow, Decision Rules, Escalation.
- Before: Claude live research calls and MCP retrieval tool permission were not explicitly auto-approved by this skill.
- After: Standard/deep public research lets Codex approve the Claude call and the Exa/Firecrawl MCP search/fetch/scrape allowlist without another user prompt.
- Why: The user requested autonomous Codex approval for Claude research and MCP retrieval tools.
- Impact: Research execution can use Claude MCP retrieval directly while private/restricted data and broader tools remain blocked.
- Validation: Workspace and deployed validation passed.
- Detail record: ../entries/2026/2026-08/CR-20260821-001-auto-approved-mcp-research.md

### CR-20260810-001 - strong-research-gate

- Section changed: SKILL.md Operating Rules, Workflow, Decision Rules, References.
- Before: light research could use a lightweight path without an explicit user-confirmed downgrade step.
- After: every research invocation enters the strong gate by default; light research is only allowed after Codex judges the task simple enough and the user confirms the downgrade.
- Why: The user wants research calls to execute the full gate unless a simple-case exception is explicitly approved.
- Impact: standard/deep behavior stays unchanged; light-mode now becomes an explicit, user-approved exception.
- Validation: Pending.
- Detail record: ../entries/2026/2026-08/CR-20260810-001-strong-research-gate.md

### CR-20260809-002 - live-adapter-cleanliness

- Section changed: Operating Rules, Workflow, Decision Rules.
- Before: Live adapter failures were recoverable only through general repair language.
- After: Live adapter runs must end with schema-valid structured artifacts; malformed feedback or flat workspace layout is classified as repair-needed until repaired and validated.
- Why: The live execution left raw malformed feedback and an initially flat layout behind, which made the run harder to review and reuse.
- Impact: Future live runs now have a clearer cleanup boundary before validation or deployment.
- Validation: Workspace validation passed.
- Detail record: ../entries/2026/2026-08/CR-20260809-002-live-adapter-cleanliness.md

### CR-20260809-001 - claude-loop-workflow

- Section changed: Operating Rules, Workflow, Decision Rules, Validation, Escalation.
- Before: No Codex-Claude two-round loop or severity rules.
- After: Skill implements adapter-agnostic Claude integration, two-round loop, fallback rules, severity rules.
- Why: PRD v1.2 requires governable two-round research with Codex planning and Claude execution.
- Impact: Standard and deep research now require the full two-round loop.
- Validation: Workspace copy validated.
- Detail record: ../entries/2026/2026-08/CR-20260809-001-claude-research-loop.md

### CR-20260908-002 - Research routing split

- Section changed: approved candidate routing/identity boundary.
- Before: generic research was the Claude execution entry.
- After: generic router and retained guided execution are separate.
- Why: approved research-routing review.
- Impact: research-guided; no global writes.
- Validation: candidate evidence in development workspace; initially pending.
- Detail record: [record](../entries/2026/2026-09/CR-20260908-002-research-routing.md).
