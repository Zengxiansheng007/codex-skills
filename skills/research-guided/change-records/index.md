# Change Records

## Latest Changes

| Date | Change ID | Summary | Status |
|---|---|---|---|
| 2026-09-08 | CR-20260908-002 | Research routing split candidate | validated / candidate only |
| 2026-08-29 | CR-20260829-001 | Normalize live Claude gap severity aliases and require complete zero-P0/P1 acceptance. | validated-candidate |
| 2026-08-27 | CR-20260827-001 | Add two-stage adapter-validated Research compatibility mode, evidence ledger, tool-free serialization, bounded format retries, local validation, and adapter failure propagation. | validated-candidate |
| 2026-08-25 | CR-20260825-002 | Add Exa stdio bridge, live Research runner, provider-denial evidence, and open P0/P1 completion gate. | validated |
| 2026-08-25 | CR-20260825-001 | Repair research execution chain: plan mode block, tool registry, preflight, result schema, failure classification, downstream sync. | validated |
| 2026-08-21 | CR-20260821-001 | Allow Codex to self-approve Claude public research calls and approved Exa/Firecrawl MCP retrieval tools. | validated |
| 2026-08-10 | CR-20260810-001 | Make research default to strong gate and require user confirmation for light-path downgrade. | validated |
| 2026-08-09 | CR-20260809-002 | Tighten live adapter output hygiene and repair handling. | validated |
| 2026-08-09 | CR-20260809-001 | Implement Codex-Claude two-round research loop. | validated |

## Category Index

| Category | Path |
|---|---|
| Core Skill Markdown | categories/core-skill-md.md |
| References And Assets | categories/references-and-assets.md |
| Scripts And Validation | categories/scripts-and-validation.md |
| Safety And Governance | categories/safety-and-governance.md |
| Downstream And Handoff | categories/downstream-and-handoff.md |
## Open Risks

- Light-path downgrade must remain user-confirmed; any silent downgrade is a regression.
- Global skill deployment requires explicit user approval after Codex independent validation.
- Auto-approved Claude retrieval is limited to public research and the explicit Exa/Firecrawl MCP allowlist; any broader tool or data request remains blocked pending approval.
- Tests and validators for the research repair (CR-20260825-001) must be executed once tool permissions allow Python execution; implementation is complete but execution is pending.
- Downstream skills (handoff-claude-executor, handoff-feedback-reviewer) must reference the new failure classes in future updates to ensure full propagation.

Current candidate detail: [CR-20260908-002](entries/2026/2026-09/CR-20260908-002-research-routing.md).
