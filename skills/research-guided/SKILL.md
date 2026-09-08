---
name: research-guided
description: Use when the research router selects this branch, the user explicitly chooses Claude or Codex, or invokes research-guided. Execute the preserved research workflow when the research router selects this branch, the user explicitly chooses Claude or Codex retrieval, or invokes research-guided. Default to Claude first except explicit Codex selection; generic research requests belong to the research router.
---

# Research Guided

## Router Entry Compatibility

This is the original research execution Skill, retained under its new identity. Read [entry compatibility](references/router-entry-compatibility.md) before choosing the executor. The approved explicit Codex choice is an entry exception; legacy Claude-specific instructions below apply to the Claude profile. Preserve all original quality gates.

## Operating Rules

- Codex owns the research direction, outline design, final review, reinforcement decision, and result gate.
- Claude acts as a specialist retrieval executor with structured output and approval boundaries.
- Every research invocation must enter the strong-gate flow by default.
- Standard and deep research must use the Codex-Claude two-round loop.
- When Codex needs Claude for standard or deep public research, Codex self-approves the Claude live retrieval call without asking the user again, provided the data boundary is public-only and the action stays inside this skill's adapter contract.
- Codex self-approves Claude use of these read-only MCP retrieval tools during research: `mcp__exa__web_search_exa`, `mcp__exa__web_fetch_exa`, `mcp__firecrawl__firecrawl_search`, and `mcp__firecrawl__firecrawl_scrape`.
- Light research is an explicit exception and may use a lightweight path only after Codex judges the task simple enough and the user confirms the downgrade; even then, the result and rationale must still be recorded.
- At most one mandatory reinforcement round; after the second round, remaining P0/P1 gaps produce partial, blocked, or rerun results with recorded design defects.
- P0 packet fields missing means direct failure; P1 issues require user confirmation; P2 format issues may be repaired by Codex and logged.
- When Claude is unavailable, default to blocked and ask the user before using Codex fallback retrieval.
- Private documents, internal paths, screenshots, and business data are not sent to Claude by default; they require separate confirmation.
- The Claude adapter is adapter-agnostic; the default implementation supports Claude Code CLI or SDK as a replaceable adapter.
- Live adapter runs must end with schema-valid structured artifacts; if the raw packet is malformed or the workspace is written in a flat layout, treat the run as repair-needed, preserve the raw evidence, repair the workspace copy, and rerun validation before any global deployment request.
- When changing this skill, create or update traceable change records using [the change record traceability contract](references/change-record-traceability.md).
- Do not deploy, publish, delete, migrate, or run destructive actions without explicit approval.
- Do not install dependencies, use network retrieval, or access external private systems without approval.
- **Live research must reject permission mode plan** (FR-RR-001). Plan mode cannot execute tools and will stall the research loop. Allowed modes: `default`, `acceptEdits`, `auto`, `dontAsk`.
- **One JSON registry owns the four approved MCP tool names** (FR-RR-002). The registry at `schemas/public-research-tool-registry.json` is the single source of truth. Use `scripts/check_tool_drift.py` to detect drift.
- **Preflight must verify** executable, CLI capability, fresh session, MCP schema visibility, tool count, exact registry match, canary evidence, and zero permission denials before live research (FR-RR-003). Use `scripts/preflight_research.py`.
- **Research output must be pure UTF-8 JSON** validated by `schemas/research-result.schema.json` (Draft 2020-12) and semantic evidence gates (FR-RR-004). Use `scripts/validate_research_result.py`.
- **Format retries and content reinforcement are separate and bounded** (FR-RR-005). Format repair: max 3 retries without new retrieval. Content reinforcement: max 1 round. Use `scripts/live_mode_guard.py`.
- **Stable failure classes propagate** through research, handoff executor, feedback reviewer, and development-system contracts (FR-RR-006). See `schemas/failure-classification.json`.
- **Two-stage adapter-validated compatibility mode is explicit** (FR-ADP-001). The run records `schemaEnforcementMode` (`provider-native` or `adapter-validated`) and `providerNativeSchema` honestly. Activation cannot occur silently after a provider-native failure; the `adapter-validated` profile is selected only by an explicit profile, never as a silent downgrade.
- **Retrieval and serialization are separate phases with separate tool boundaries** (FR-ADP-002). Retrieval uses only the approved public MCP registry; serialization exposes no retrieval, shell, browser, filesystem-write, or network tools.
- **Retrieval evidence is frozen before serialization** (FR-ADP-003). Queries, tool calls, permission results, sources, content digests, timestamps, session lineage, boundary checks, and the registry hash are persisted into `schemas/research-evidence-ledger.schema.json` and canonical-hashed. See `scripts/serialize_research.py`.
- **Serialization cannot introduce unsupported facts** (FR-ADP-004). Every final source, URL, claim, and claim-source mapping must resolve to the frozen evidence ledger; additions fail validation.
- **Local validation is the acceptance authority** (FR-ADP-005). Draft 2020-12 Schema validation and semantic gates pass before an output can claim complete, in both modes.
- **Format repair is bounded and performs no retrieval** (FR-ADP-006). At most three serialization attempts are recorded; all use the same evidence hash; exhaustion returns `blocked` or `repair-needed`, never `complete`.
- **Provider-native behavior remains available and unchanged** (FR-ADP-007). Native-mode regression tests pass; compatibility mode is selected only by an explicit profile.
- **Failures propagate without false completion** (FR-ADP-008). Tool denial, missing URL, invalid Schema, source drift, new facts, retry exhaustion, timeout, or sensitive output cannot produce `complete`.
- **Real runtime integration is required but separately approved** (FR-ADP-009). A fresh GLM 5.2 session performs a real approved Exa search and produces a final Research packet with zero P0/P1 findings. Do not execute the live canary in a development-only packet.
- **Candidate and global deployment states remain separate** (FR-ADP-010). Candidate validation does not change global Skills; installation requires exact source hash, backup, atomic replacement, rollback, and separate approval.

## scholar-deep-research Compatibility Bridge

The optional compatibility bridge under `scripts/compatibility/` and
`fixtures/compatibility/` connects an accepted Research result to the fixed
`scholar-deep-research` baseline without replacing its `research_state.py`,
Phase 0..7, G1..G7, ranking, triage, citation-chase, report, or export
contracts. Use `complete_pipeline.py` only with an actual frozen ledger and a
lineage-bound pipeline plan. Fixture runs report `test-completed`; only a
`live-scholarly` plan with real scholarly evidence may report product
completion. Standards, tool documentation, Claude documentation, and ordinary
web pages remain evidence-only when no DOI, OpenAlex, arXiv, or PMID identity is
present.

## Workflow

1. Classify research depth:
   - **light-candidate**: only when the task is objectively simple and Codex is considering a downgraded path; pause and ask the user for confirmation before using a lightweight path.
   - **standard**: must use the Codex-Claude two-round loop.
   - **deep**: must use the Codex-Claude two-round loop with deeper source coverage.
   - If the user does not confirm the downgrade, treat the task as **standard** and continue with the strong-gate flow.
2. Design research direction and outline (Codex):
   - define topic scope, priorities, exclusions, and expected source types;
   - produce a structured outline for Claude to execute item by item;
   - record the direction and outline in the research packet.
3. Execute first-round retrieval (Claude):
   - Claude retrieves sources according to the Codex outline;
   - Codex supplies the research adapter with the approved MCP allowlist for public search and fetch/scrape tools;
   - Codex may approve the Claude live call and allowed MCP tool use directly when the task is standard/deep public research and no private, login-gated, paid, internal, or restricted source is required;
   - Claude produces structured output with sources, claims, gaps, and initial review;
   - read [the Claude adapter contract](references/claude-adapter-contract.md) for adapter invocation details.
4. Review coverage and identify gaps (Codex):
   - compare Claude output against the outline and requirement artifacts;
   - classify gaps and defects by severity (P0, P1, P2);
   - read [the severity and fallback rules](references/severity-and-fallback-rules.md) for decision rules.
5. Decide reinforcement or closure (Codex):
   - if P0/P1 gaps exist, initiate at most one reinforcement round;
   - produce a targeted gap list for Claude to address;
   - if no P0/P1 gaps remain, proceed to final review.
6. Execute reinforcement round (Claude, if triggered):
   - Claude addresses the targeted gap list;
   - Codex reuses the same approved MCP allowlist unless the gap list needs a new restricted data source or tool;
   - Claude produces updated structured output with gap closure status.
   - if the live adapter output is structurally dirty, repair the workspace copy and rerun validation before continuing.
7. Final review and decision gate (Codex):
   - assess whether coverage is complete across requirements, development plan, and test plan;
   - decide: pass, partial, blocked, or rerun;
   - read [the decision gate rules](references/decision-gate-rules.md) for the decision matrix.
8. Handle Claude unavailability:
   - default to blocked;
   - ask the user before using Codex fallback retrieval unless a separate active requirement anchor explicitly preauthorizes that fallback;
   - record the fallback decision and user confirmation.
9. Produce the research report:
   - include direction, outline, round-one results, gap analysis, reinforcement results, final decision, and evidence index;
   - record all rounds, sources, queries, gaps, and closure trails.
10. Record change traceability:
   - if this skill was changed, update [the change record system](references/change-record-traceability.md).

## Decision Rules

- Light research is not automatic; it requires a Codex simple-task judgment and explicit user confirmation.
- If the user does not confirm a light-path downgrade, continue with the strong-gate flow.
- If research depth is light after confirmation, a simplified path is allowed but results and rationale must still be recorded.
- If Claude is unavailable, default to blocked; do not silently fall back to Codex retrieval.
- For standard/deep public research, Codex approval of the Claude call and approved MCP retrieval tools is automatic and does not require another user prompt.
- Automatic approval is limited to public search, public fetch/scrape, and structured evidence return. It does not cover private repositories, login-gated pages, paid sources, internal systems, credentials, destructive actions, dependency installation, or arbitrary shell/network tools.
- If Claude requests any MCP tool outside `mcp__exa__web_search_exa`, `mcp__exa__web_fetch_exa`, `mcp__firecrawl__firecrawl_search`, or `mcp__firecrawl__firecrawl_scrape`, Codex must classify it as a tool-scope mismatch and decide whether to block or request a new approval.
- If P0 fields are missing from a Claude packet, the feedback is invalid and the loop stops.
- If P1 issues exist, require user confirmation before proceeding.
- If P2 format issues exist, Codex may repair and log them without blocking.
- If the second round still has P0/P1 gaps, output partial, blocked, or rerun with a defect matrix.
- If a live adapter run returns malformed feedback or a flat workspace layout, classify the run as repair-needed until the structured artifacts validate.
- If sensitive content would be sent to Claude without confirmation, block and ask.
- If the adapter cannot be resolved, block and ask the user for direction.

## Validation

Run these after creating or changing this skill:

```powershell
python scripts/validate_research_skill.py <skill-folder>
```

For file-changing updates to this skill:

```powershell
python scripts/validate_research_skill.py <skill-folder> --require-change-records
python scripts/test_research_skill.py
```

Research repair validation (FR-RR-001 through FR-RR-006):

```powershell
python scripts/test_research_repair.py
python scripts/preflight_research.py --permission-mode default --session-id test --session-started-at 2026-08-25T10:00:00Z --visible-tools mcp__exa__web_search_exa mcp__exa__web_fetch_exa mcp__firecrawl__firecrawl_search mcp__firecrawl__firecrawl_scrape --requested-tools mcp__exa__web_search_exa mcp__exa__web_fetch_exa mcp__firecrawl__firecrawl_search mcp__firecrawl__firecrawl_scrape --canary-json "{\"canaryPassed\":true,\"canaryDetail\":\"ok\"}" --skip-cli
python scripts/live_mode_guard.py --mode live --permission-mode default --requested-tools mcp__exa__web_search_exa mcp__exa__web_fetch_exa mcp__firecrawl__firecrawl_search mcp__firecrawl__firecrawl_scrape
python scripts/check_tool_drift.py
```

Sensitive scan:

```powershell
python scripts/scan_sensitive.py <skill-folder>
```

Two-stage adapter validation (FR-ADP-001 through FR-ADP-010):

```powershell
python scripts/test_research_adapter.py
python scripts/serialize_research.py --ledger <frozen-ledger.json> --candidate <serialization-candidate.json>
```

The adapter tests cover unit (ledger freezing, canonical hashing, retry counting,
candidate extraction, source/claim mapping), contract (Schema + semantic gates
for both modes), integration (fake retrieval transcript through both stages),
negative (prose-around-json, malformed JSON, missing field, ledger-absent URL
and claim, serialization tool access, permission denial, evidence hash change,
three failed attempts, silent downgrade), regression (provider-native mode),
cross-skill failure-class propagation, and sensitive scans. No live external
call is executed by these tests.
Forward-test prompt example:

```text
Use research to do a standard-depth investigation on [topic] and produce a structured report with evidence.
```

Do not include the expected final report in the test prompt.

## Escalation

Ask before:

- installing packages or validators;
- writing to the global Codex skills directory;
- executing target skill scripts;
- using GitHub/private repositories;
- sending skill content to external LLMs;
- changing production systems, accounts, credentials, or global configuration;
- using Codex fallback retrieval when Claude is unavailable;
- allowing Claude to use MCP tools outside the approved public-research allowlist;
- sending private documents, internal paths, screenshots, or business data to Claude.
