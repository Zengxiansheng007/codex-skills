# Claude Adapter Contract

The research skill calls Claude through an adapter-agnostic interface. The default implementation supports Claude Code CLI or SDK as a replaceable adapter.

## Adapter Interface

Every adapter must implement:

1. `invoke(prompt, schema, options)` - execute a Claude retrieval round.
2. `parse_output(raw)` - parse Claude output into structured JSON.
3. `check_availability()` - return whether Claude is currently available.
4. `get_adapter_name()` - return the adapter identifier.

## Default CLI Adapter

The default adapter uses Claude Code CLI in non-interactive print mode:

- Command: `claude --permission-mode default --allowedTools "mcp__exa__web_search_exa,mcp__exa__web_fetch_exa,mcp__firecrawl__firecrawl_search,mcp__firecrawl__firecrawl_scrape" --output-format json -p "<prompt>"`
- Output: structured JSON validated against the expected schema.
- Availability: checked by verifying the CLI executable exists.
- **Workspace MCP transport fallback:** when Claude Code's remote HTTP MCP
  transport remains in `pending`/`Failed to connect`, the candidate workspace
  may load `exa-stdio-mcp.json` (or the project `.mcp.json`) to run
  `scripts/exa_mcp_bridge.py`. The bridge is UTF-8 stdio, forwards only the
  MCP initialize/tools/list/tools/call/ping methods, and sends Exa the required
  `Accept: application/json, text/event-stream` header. It is workspace-local
  and carries no credentials; global Claude configuration is never changed.
- **Plan mode is explicitly forbidden for live research** (FR-RR-001). The adapter must reject `--permission-mode plan` before spawning Claude, because plan mode cannot execute tools and will stall the research loop.
- Allowed permission modes for live research: `default`, `acceptEdits`, `auto`, `dontAsk`.

## Public Research MCP Allowlist

Codex may self-approve these Claude Code MCP tools for standard and deep public research:

- `mcp__exa__web_search_exa`
- `mcp__exa__web_fetch_exa`
- `mcp__firecrawl__firecrawl_search`
- `mcp__firecrawl__firecrawl_scrape`

The allowlist is read-only and source-discovery focused. It authorizes public web search, public page fetch, and public page scrape for evidence collection. It does not authorize arbitrary shell commands, browser control, authenticated sources, paid sources, private repositories, internal systems, account actions, credential export, dependency installation, writes, deletes, publishing, or production access.

The adapter must record the exact allowed tools in the run manifest. If Claude requests a tool outside the allowlist, Codex must treat the attempt as a tool-scope mismatch and stop or request a new approval.

For public research runs, the adapter should prefer explicit `--allowedTools` over global permission bypass. Do not use `--dangerously-skip-permissions` or `--permission-mode bypassPermissions` as the default research path.

## Public Research MCP Tool Registry (FR-RR-002)

The single JSON registry at `schemas/public-research-tool-registry.json` owns the four approved MCP tool names. All references in SKILL.md, reference files, scripts, manifests, and runtime configuration must match this registry exactly. Use `scripts/check_tool_drift.py` to detect drift.

## Preflight Contract (FR-RR-003)

Before any live research attempt, the adapter must run `scripts/preflight_research.py` and verify:

1. Claude executable exists.
2. CLI capability (version check).
3. Fresh session declaration (session_id and session_started_at are present and valid).
4. MCP schema visibility (at least one registry tool is visible).
5. Tool count > 0.
6. Exact registry match (no unregistered tools requested).
7. Canary evidence present and passed.
8. Zero permission denials.
9. Permission mode is not plan.

Live research must fail closed when any of these checks fail. The preflight result must be recorded in the run manifest.

## Research Result Schema (FR-RR-004)

Research output must be pure UTF-8 JSON (no BOM, no prose wrapper) validated against `schemas/research-result.schema.json` (Draft 2020-12) and semantic evidence gates enforced by `scripts/validate_research_result.py`.

Semantic gates require:
- `sessionFresh` is true.
- `evidenceComplete` is true only when all sources are verified.
- `toolRegistryMatch` is true.
- `permissionDenials` is 0.
- `permissionMode` is not plan.
- `toolCount` > 0.
- `mcpSchemaVisible` is true.
- `canaryEvidence.canaryPassed` is true.
- Source mappings are valid (each claim's `sourceUrl` exists in `sources`).
- `formatRetries` ≤ 3.
- `reinforcementRounds` ≤ 1.
- Unverified sources are not claimed complete.

## Format Retries and Reinforcement Bounds (FR-RR-005)

- Format repair may retry serialization at most 3 times without new retrieval.
- Content gaps allow at most 1 reinforcement round.
- Format retries and content reinforcement are separate: format retries fix serialization without new retrieval, while reinforcement rounds address content gaps with new retrieval.

## Stable Failure Classification (FR-RR-006)

Failure classes are defined in `schemas/failure-classification.json` and propagate through research, handoff executor, feedback reviewer, and development-system contracts. Each failure class has a severity (P0 or P1) and a propagation status (e.g., `repair-needed`, `blocked-external-dependency`, `blocked-user-decision`).

## Two-Stage Adapter-Validated Compatibility Mode (FR-ADP-001..010)

When the gateway/model combination cannot enforce the Schema at generation time
(`structured-output-empty`, confirmed for `bailian/glm-5.2` + Claude Code with
`--json-schema`), the explicit `adapter-validated` compatibility profile keeps
the gateway and model unchanged while restoring fail-closed structured Research.

### Explicit Mode (FR-ADP-001)

- The run records `schemaEnforcementMode` (`provider-native` or
  `adapter-validated`) and `providerNativeSchema` honestly.
- `adapter-validated` records `providerNativeSchema=false`. It is selected
  only by an explicit profile and never silently after a provider-native
  failure (`silent-native-downgrade` is a P0 failure).

### Separate Phases And Tool Boundaries (FR-ADP-002)

- Stage one (retrieval/evidence-freeze) uses only the approved public MCP
  registry and records every tool call, permission result, source, and boundary
  check.
- Stage two (tool-free serialization) exposes no retrieval, shell, browser,
  filesystem-write, or network tools. Any such tool is a P0
  `serialization-tool-access` failure.

### Frozen Evidence Ledger (FR-ADP-003)

`scripts/serialize_research.freeze_ledger` persists session identity, queries,
tool calls, permission results, sources (with content digests), registry hash,
boundary checks, and timestamps into a ledger conforming to
`schemas/research-evidence-ledger.schema.json`. The ledger body is
canonical-hashed into `ledgerSha256` (the field is excluded from its own hash).

### Serialization Cannot Introduce Unsupported Facts (FR-ADP-004)

`scripts/serialize_research.validate_against_ledger` rejects any final source,
URL, claim, or claim-source mapping absent from the frozen ledger
(`unsupported-fact-introduced`, P0).

### Local Validation Authority (FR-ADP-005)

`scripts/validate_research_result.py` is the acceptance authority. In
`adapter-validated` mode the provider-native-only gates
(`toolRegistryMatch`, `toolCount`, `mcpSchemaVisible`, `canaryEvidence`) are
inherited from the frozen ledger; local Schema and semantic gates remain
mandatory.

### Bounded Format Repair (FR-ADP-006)

`scripts/serialize_research.serialize_with_ledger` records at most three
format attempts, all bound to one unchanged evidence hash
(`evidence-hash-unstable`, P0 if violated). Exhaustion returns `blocked` or
`repair-needed`, never `complete`.

### Provider-Native Unchanged (FR-ADP-007)

Provider-native mode remains available and unchanged. Native-mode regression
tests pass; the adapter is selected only by an explicit profile.

### Failure Propagation (FR-ADP-008)

Failures (tool denial, missing URL, invalid Schema, source drift, new facts,
retry exhaustion, timeout, sensitive output) propagate without false
completion. See the adapter failure classes in
`schemas/failure-classification.json` and the propagation table in
`references/downstream-and-handoff.md`.

### Real Runtime Integration (FR-ADP-009)

A fresh GLM 5.2 session performing a real approved Exa search and producing a
final Research packet with zero P0/P1 findings is required for acceptance. It
is executed only after exact live approval and never in a development-only
packet.

### Candidate And Global Separation (FR-ADP-010)

Candidate validation changes only staged candidate files. Global installation
requires exact source hash, backup, atomic replacement, rollback, and separate
approval.

## Output Hygiene

Every live run must write to a dedicated output directory and preserve the raw and repaired evidence separately:

- `manifest.json`
- `stdout.json`
- `stdout.txt`
- `stderr.txt`
- `feedback.raw.json` when the adapter output is malformed
- `feedback.json` only after schema validation or Codex repair

If the adapter cannot create the expected directory structure or emits malformed feedback, the run is `repair-needed`, not complete.
## SDK Adapter Alternative

An alternative adapter uses the Claude Agent SDK:

- Invoked programmatically with structured output schema.
- Supports approval callbacks for tool use.
- Returns JSON validated against the expected schema.

## Adapter Replacement

To replace the adapter:
1. Implement the four interface methods.
2. Register the adapter in the skill configuration.
3. Run validation to confirm the new adapter produces compatible output.
4. No changes to `SKILL.md` workflow are needed; the adapter is transparent.
## Unavailability Handling

When `check_availability()` returns false:
1. Default to blocked status.
2. Ask the user before using Codex fallback retrieval unless a separate active requirement anchor explicitly preauthorizes that fallback.
3. Record the unavailability event and user decision.
4. Do not silently fall back to Codex retrieval.

## Sensitive Content Boundary

- Private documents, internal paths, screenshots, and business data are not sent to Claude by default.
- If sensitive content is needed, require separate user confirmation before including it in the Claude prompt.
- Record the confirmation and the scope of sensitive content sent.
