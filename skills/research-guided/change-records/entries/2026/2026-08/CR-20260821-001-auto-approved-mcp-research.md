# CR-20260821-001 - Auto Approved MCP Research

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | research |
| Change Type | governance |
| Scope | core-skill-md / references-and-assets / safety-and-governance / downstream-and-handoff |
| Source | user request |
| Baseline | SKILL.md SHA-256 `FFD715CE1ECAFBF02F9C156F16CBA13B19EE32B33D93D748D38C626F68228F4B`; baseline validators passed with P0/P1/P2 = 0 |
| Author | Codex |
| Related Records | CR-20260810-001 |

## Summary

Allow Codex to self-approve Claude Code public research calls and explicitly allow the Exa/Firecrawl MCP retrieval tools required for standard and deep research.

## Context And Problem

Claude Code previously had no connected search MCP tools, so research attempts could degrade into ad hoc PowerShell/curl retrieval and timeout without stdout/stderr. After Exa and Firecrawl MCP were installed and smoke-tested, the research skill needed a clear approval and allowlist contract so Codex can invoke Claude retrieval without repeatedly asking the user.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `SKILL.md` | Operating Rules | Added Codex self-approval for standard/deep public Claude research and the Exa/Firecrawl MCP allowlist. |
| `SKILL.md` | Workflow | Added allowlist injection for first and reinforcement rounds. |
| `SKILL.md` | Decision Rules / Escalation | Added public-only auto-approval limits and blockers for non-allowlisted tools or restricted data. |
| `references/claude-adapter-contract.md` | Default CLI Adapter / Public Research MCP Allowlist | Updated default command to use `--allowedTools`; added allowlist and no-bypass rule. |
| `references/severity-and-fallback-rules.md` | Fallback Rules | Added Claude public research auto-approval rules and scope mismatch handling. |
| `change-records/*` | Index and ledgers | Recorded the change in impacted ledgers. |

## Decision And Alternatives

Selected explicit `--allowedTools` because it gives Claude access to the required retrieval MCP tools without using global permission bypass. Rejected `--dangerously-skip-permissions` as a default because it would authorize more than public research retrieval.

## Detailed Change

The approved MCP allowlist is:

- `mcp__exa__web_search_exa`
- `mcp__exa__web_fetch_exa`
- `mcp__firecrawl__firecrawl_search`
- `mcp__firecrawl__firecrawl_scrape`

Codex may approve these tools only for public search, public fetch, public scrape, and structured evidence return. Restricted sources, private data, account actions, writes, installs, and arbitrary shell/network tools remain blocked.

## Impact Analysis

- Standard/deep research no longer needs a fresh user prompt merely to call Claude or allow these retrieval tools.
- Claude output still must pass schema, source coverage, sensitive-boundary, and Codex final review gates.
- Codex fallback retrieval remains blocked unless separately authorized or already covered by an active requirement anchor.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Baseline research validator | `python scripts/validate_research_skill.py <candidate> --require-change-records` before edits | Passed | P0/P1/P2 = 0 |
| Baseline create-skill validator | `python scripts/validate_create_skill.py <candidate> --require-change-records` before edits | Passed | P0/P1/P2 = 0 |
| Workspace research validator | `python scripts/validate_research_skill.py <candidate> --require-change-records` | Passed | P0/P1/P2 = 0 |
| Workspace create-skill validator | `python scripts/validate_create_skill.py <candidate> --require-change-records` | Passed | P0/P1/P2 = 0 |
| Sensitive scan | `python scripts/scan_sensitive.py <candidate>` | Passed | No secret findings |
| Deployed validation | Post-deploy validators | Passed | P0/P1/P2 = 0 |

## Safety And Privacy

No secrets, credentials, private URLs, account data, or production-only commands were added. The rule is explicitly public-only and preserves blockers for private, login-gated, paid, internal, or restricted sources.

## Risks And Follow-up

- If future MCP tool names change, the allowlist must be updated and smoke-tested.
- Firecrawl should remain a fetch/scrape補证 tool unless a future smoke test proves its search path is stable in Claude Code.

Refs:

- `SKILL.md`
- `references/claude-adapter-contract.md`
- `references/severity-and-fallback-rules.md`
