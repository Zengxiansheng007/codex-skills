# References And Assets Change Ledger

## Purpose

Record changes to references, fixtures, templates, or schemas.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-08-25 | CR-20260825-001 | claude-adapter-contract / severity-and-fallback-rules / downstream-and-handoff | governance | Add tool registry, preflight contract, result schema, failure classification, downstream propagation. | validated |
| 2026-08-21 | CR-20260821-001 | claude-adapter-contract / severity-and-fallback-rules | governance | Document public-research MCP allowlist and fallback boundary changes. | validated |
| 2026-08-10 | CR-20260810-001 | references/strong-gate-and-light-path.md | added | Add explicit strong-gate and user-confirmed light-path reference. | validated |
| 2026-08-09 | CR-20260809-002 | claude-adapter-contract / severity-and-fallback-rules | updated | Tighten live adapter output hygiene and repair handling. | validated |
| 2026-08-09 | CR-20260809-001 | references/ | added | Add traceability, adapter, severity, and decision gate references. | validated |
## Detailed Records

### CR-20260825-001 - research-repair-references

- Section changed: references/claude-adapter-contract.md, references/severity-and-fallback-rules.md, references/downstream-and-handoff.md.
- Before: References did not define tool registry, preflight contract, result schema, failure classification, or downstream propagation.
- After: References define all six FR-RR contracts and downstream failure class propagation table.
- Why: The execution chain needs explicit contracts for each fail-closed condition.
- Impact: Clearer adapter, severity, and downstream routing for research runs.
- Validation: Pending execution due to tool permission restriction.
- Detail record: ../entries/2026/2026-08/CR-20260825-001-research-repair.md

### CR-20260821-001 - auto-approved-mcp-research

- Section changed: references/claude-adapter-contract.md and references/severity-and-fallback-rules.md.
- Before: References did not define the Exa/Firecrawl allowlist or the public-only self-approval rule.
- After: References define public-only auto-approval, approved MCP tools, scope mismatches, and fallback limits.
- Why: The execution contract must match the user's requested unattended Claude retrieval behavior.
- Impact: Clearer adapter and severity routing for future research runs.
- Validation: Workspace and deployed validation passed.
- Detail record: ../entries/2026/2026-08/CR-20260821-001-auto-approved-mcp-research.md

### CR-20260810-001 - strong-gate-reference

- Section changed: references/strong-gate-and-light-path.md.
- Before: No dedicated reference described the mandatory strong gate versus the user-confirmed light-path exception.
- After: Added a focused reference that defines the default strong gate, simple-case criteria, the user-confirmed downgrade rule, recording requirements, and anti-patterns.
- Why: Keep SKILL.md concise while making the new gate behavior explicit and reusable.
- Impact: Future maintenance can point at one reference instead of re-encoding the same rules in the workflow body.
- Validation: Pending.
- Detail record: ../entries/2026/2026-08/CR-20260810-001-strong-research-gate.md

### CR-20260809-002 - live-adapter-cleanliness

- Section changed: references/claude-adapter-contract.md, references/severity-and-fallback-rules.md.
- Before: Adapter contract described structured output but did not explicitly preserve raw malformed feedback or define flat-layout cleanup.
- After: Live runs must write dedicated structured artifacts, preserve raw feedback separately, and treat malformed feedback or flat layout as repair-needed.
- Why: The previous live run produced malformed feedback and a flat file layout, which were recoverable but not clean.
- Impact: Reference guidance now makes the cleanup boundary explicit for future live execution.
- Validation: Workspace validation passed.
- Detail record: ../entries/2026/2026-08/CR-20260809-002-live-adapter-cleanliness.md

### CR-20260809-001 - references-added

- Section changed: references/.
- Before: No reference files existed.
- After: Added change-record-traceability, claude-adapter-contract, severity-and-fallback-rules, decision-gate-rules.
- Why: SKILL.md should stay concise while long rules live in references/.
- Validation: Links resolve from SKILL.md.
- Detail record: ../entries/2026/2026-08/CR-20260809-001-claude-research-loop.md

### CR-20260908-002 - Research routing split

- Section changed: approved candidate routing/identity boundary.
- Before: generic research was the Claude execution entry.
- After: generic router and retained guided execution are separate.
- Why: approved research-routing review.
- Impact: research-guided; no global writes.
- Validation: candidate evidence in development workspace; initially pending.
- Detail record: [record](../entries/2026/2026-09/CR-20260908-002-research-routing.md).
