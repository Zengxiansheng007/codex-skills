# CR-20260825-002 - Live MCP Bridge And Completion Gap Gate

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | research |
| Change Type | runtime-integration / validation |
| Scope | scripts-and-validation / references-and-assets |
| Source | live Claude/Exa integration evidence |
| Baseline | CR-20260825-001 candidate workspace |

## Summary

Add a UTF-8 stdio MCP bridge for Exa because Claude Code 2.1.178 did not complete
the remote Streamable HTTP negotiation in this environment, and add a bounded
live Research runner that executes mode guard, preflight, Claude retrieval, and
independent result validation. Completion is now blocked when P0/P1 coverage
gaps remain open.

## Changes

- `scripts/exa_mcp_bridge.py` forwards MCP initialize, tools/list, tools/call,
  and ping over the Exa HTTP endpoint with the required JSON+SSE Accept header.
- `.mcp.json` and `exa-stdio-mcp.json` register the bridge in the candidate
  workspace only; no user-level Claude configuration is changed.
- `scripts/run_live_research.py` persists live-mode guard, preflight, raw Claude
  output, research result, manifest, and validator evidence. Provider permission
  denials are authoritative and cannot be masked by model-authored fields.
- `validate_research_result.py` rejects `completionClaim=complete` when
  `p0p1Gaps` or `gaps` contains unresolved P0/P1 entries.
- `test_research_repair.py` adds a regression for the completion gap gate.

## Context And Problem

The remote HTTP MCP endpoint was reachable by direct JSON-RPC diagnostics but
Claude Code 2.1.178 left the server in `pending` and exposed no callable Exa
schema. The first live Research result also showed that model-authored schema
claims and gap severities need independent enforcement.

## Sections Changed

| File | Change |
|---|---|
| `scripts/exa_mcp_bridge.py` | UTF-8 stdio bridge for Exa streamable HTTP |
| `.mcp.json`, `exa-stdio-mcp.json` | Workspace-only MCP registration |
| `scripts/run_live_research.py` | Guarded live Research orchestration and evidence |
| `scripts/validate_research_result.py` | Block complete results with open P0/P1 gaps |
| `scripts/test_research_repair.py` | Regression coverage for the new completion gate |

## Decision And Alternatives

The candidate uses a stdio bridge because it preserves the approved Exa tool
boundary while compensating for the CLI transport negotiation failure. Direct
global MCP reconfiguration and unbounded permission bypass were rejected.

## Impact Analysis

Fresh Claude sessions can load Exa schemas through stdio, and live Research now
records preflight, guard, provider-denial, raw-output, and validator evidence.
Results with unresolved P0/P1 coverage gaps cannot claim completion.

## Validation Evidence

- Research repair tests: `26/26`.
- Formal Exa canary: `FEEDBACK_VALID`, one real
  `mcp__exa__web_search_exa` call, public URL returned, zero denials.
- Live Research integration: `runs/research-live-final/manifest.json` and
  `validation.json`, preflight passed, live guard passed, Exa search+fetch used,
  provider denials `0`, validator `accepted`, `P0/P1/P2 = 0`.

## Safety And Privacy

The bridge contains only a public Exa endpoint and no credentials. It forwards
only MCP protocol messages and is confined to the candidate workspace. No user
level Claude or Codex configuration was changed.

## Risks

The bridge is a candidate workspace component and must be included in the
package hash. Global Skill installation remains a separate approval gate.

## Risks And Follow-up

The remote HTTP transport may become usable after a Claude CLI upgrade; the
bridge can then be retired after a fresh canary proves the direct path. Global
deployment still requires exact installation approval and rollback evidence.
