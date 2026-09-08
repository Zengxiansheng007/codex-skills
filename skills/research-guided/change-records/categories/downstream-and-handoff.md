# Downstream And Handoff Change Ledger

## Purpose

Record changes to handoff contracts or feedback review boundaries.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-08-25 | CR-20260825-001 | downstream-and-handoff | added | Add downstream propagation contract for failure classes to handoff executor, feedback reviewer, and development system. | validated |
| 2026-08-21 | CR-20260821-001 | claude-adapter-contract | updated | Add default Claude CLI command with explicit Exa/Firecrawl MCP allowlist and no global permission bypass. | validated |
| 2026-08-09 | CR-20260809-002 | claude-adapter-contract | updated | Tighten live adapter output hygiene and repair handling. | validated |
| 2026-08-09 | CR-20260809-001 | references | added | Add adapter-agnostic Claude integration contract. | validated |
## Detailed Records

### CR-20260825-001 - downstream-propagation

- Section changed: references/downstream-and-handoff.md (new file).
- Before: No downstream propagation contract existed for research failure classes.
- After: Defines how failure classes propagate to handoff executor, feedback reviewer, and development system.
- Why: Failure classes must be stable across all contracts to prevent loss of loop state.
- Impact: Clearer downstream routing for research failures.
- Validation: Pending execution due to tool permission restriction.
- Detail record: ../entries/2026/2026-08/CR-20260825-001-research-repair.md

### CR-20260821-001 - auto-approved-mcp-research

- Section changed: references/claude-adapter-contract.md default CLI adapter and MCP allowlist.
- Before: Default CLI command did not specify the retrieval MCP allowlist.
- After: Default CLI command includes `--allowedTools` for Exa/Firecrawl public retrieval and requires manifest recording of allowed tools.
- Why: Claude Code had no search tool until MCP tools were explicitly configured and allowed.
- Impact: Downstream Claude research packets can run public retrieval without permission-denial loops.
- Validation: Workspace and deployed validation passed.
- Detail record: ../entries/2026/2026-08/CR-20260821-001-auto-approved-mcp-research.md

### CR-20260809-002 - live-adapter-cleanliness

- Section changed: references/claude-adapter-contract.md output hygiene.
- Before: The handoff path lacked an explicit clean-output boundary.
- After: Live runs must preserve raw and repaired artifacts separately and stop as repair-needed on malformed output.
- Why: The executor output should be auditable without guessing which file is authoritative.
- Impact: Cleaner handoff evidence and easier review of live runs.
- Validation: Workspace validation passed.
- Detail record: ../entries/2026/2026-08/CR-20260809-002-live-adapter-cleanliness.md

### CR-20260809-001 - adapter-contract

- Section changed: references/claude-adapter-contract.md.
- Before: No adapter contract existed.
- After: Adapter interface, CLI default, SDK alternative, replacement rules.
- Why: PRD requires adapter-agnostic design.
- Validation: Contract documented.
- Detail record: ../entries/2026/2026-08/CR-20260809-001-claude-research-loop.md

### CR-20260908-002 - Research routing split

- Section changed: approved candidate routing/identity boundary.
- Before: generic research was the Claude execution entry.
- After: generic router and retained guided execution are separate.
- Why: approved research-routing review.
- Impact: research-guided; no global writes.
- Validation: candidate evidence in development workspace; initially pending.
- Detail record: [record](../entries/2026/2026-09/CR-20260908-002-research-routing.md).
