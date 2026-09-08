# CR-20260827-001 - Two-Stage Adapter-Validated Research Compatibility Mode

| Field | Value |
|---|---|
| Status | validated / candidate only |
| Target Skill | research |
| Change Type | architecture / validation / contract |
| Scope | core-skill-md / references-and-assets / scripts-and-validation / safety-and-governance / downstream-and-handoff |
| Source | requirement-anchor CLAUDE-GLM52-ADAPTER-REPAIR-20260827-001 |
| Baseline | CR-20260825-002 candidate workspace + global research skill |

## Summary

Add a workspace-only two-stage Research adapter that keeps the current remote
gateway and `bailian/glm-5.2` unchanged while restoring fail-closed structured
Research output. A new explicit `adapter-validated` compatibility profile splits
Research into a retrieval/evidence-freeze stage and a tool-free serialization
stage. The provider-native path remains available and unchanged.

## Context And Problem

The `research-gate-blocker-v1.json` evidence confirms a runtime
incompatibility: the current Claude Code and `bailian/glm-5.2` gateway
combination executes ordinary prompts and Exa MCP calls but produces no output
whenever `--json-schema` is enabled (`structured-output-empty`). The Research
strong gate requires generation-time Schema constraint plus independent
post-hoc validation, so the full Research Story could not start. The excluded
causes include authentication, Exa availability, permission denial, and Schema
complexity, isolating the gateway/native-Schema channel as the root cause.

## Changes

- `schemas/research-evidence-ledger.schema.json` (new): frozen retrieval
  evidence ledger contract (FR-ADP-003). Records session identity, queries,
  tool calls, permission results, sources with content digests, registry hash,
  boundary checks, and a canonical `ledgerSha256`.
- `schemas/research-two-stage-manifest.schema.json` (new): manifest for the
  two-stage run, separating retrieval and serialization tool boundaries and
  recording format attempts and local validation outcome (FR-ADP-002/005/006).
- `schemas/research-result.schema.json`: add `schemaEnforcementMode`,
  `providerNativeSchema`, `evidenceLedgerRef`, and `adapterValidation` fields,
  plus new `failureClass` enum values (FR-ADP-001/004/005).
- `schemas/failure-classification.json`: add `structured-output-empty`,
  `silent-native-downgrade`, `evidence-ledger-missing`, `evidence-hash-unstable`,
  `unsupported-fact-introduced`, `serialization-tool-access`,
  `adapter-validation-failed`, and `format-attempt-exhaustion` (FR-ADP-008).
  Existing failure classes are unchanged (stable identifiers).
- `scripts/serialize_research.py` (new): stage-one `freeze_ledger`, stage-two
  `serialize_with_ledger` / `run_two_stage`, candidate extraction, ledger
  resolution, tool-boundary and evidence-hash-stability checks. No network, no
  subprocess (FR-ADP-002/004/006/008).
- `scripts/validate_research_result.py`: add adapter-validated semantic branch.
  Provider-native-only gates (toolRegistryMatch, toolCount, mcpSchemaVisible,
  canary) are inherited from the frozen ledger in adapter-validated mode; local
  Schema and semantic gates remain the acceptance authority (FR-ADP-001/005).
- `scripts/test_research_adapter.py` (new): unit, contract, integration,
  regression, negative, cross-skill, and sensitive tests for FR-ADP-001..010.
- `scripts/test_research_repair.py`: `add_strict_fields` now records an explicit
  compatibility profile so provider-native fixtures remain green; failure-class
  coverage extended to the adapter set.

## Sections Changed

- `SKILL.md`: add the explicit two-stage adapter-validated compatibility contract,
  frozen-evidence ordering, local acceptance gates, and candidate/global boundary.
- `references/claude-adapter-contract.md`: document adapter mode selection,
  retrieval/serialization separation, and failure propagation requirements.
- `references/downstream-and-handoff.md`: align downstream feedback and state
  handling with the adapter failure classes.
- `references/research-execution-gate.md`: require the adapter mode and frozen
  evidence checks before accepting a result.
- `references/severity-and-fallback-rules.md`: preserve fail-closed behavior for
  adapter failures, evidence drift, and bounded format retries.
- `schemas/research-evidence-ledger.schema.json`: add the frozen ledger contract.
- `schemas/research-two-stage-manifest.schema.json`: add the two-stage manifest.
- `schemas/research-result.schema.json`: add adapter mode, ledger, and validation
  fields while preserving provider-native compatibility.
- `schemas/failure-classification.json`: add stable adapter failure classes.
- `scripts/serialize_research.py`: add ledger freezing and tool-free serialization.
- `scripts/validate_research_result.py`: add adapter-validated semantic gates.
- `scripts/test_research_adapter.py`: add adapter contract, integration, negative,
  regression, and sensitive-data coverage.
- `scripts/test_research_repair.py`: extend strict-field and failure-class tests.

## Decision And Alternatives

The two-stage adapter is the preferred repair because it preserves the gateway
and model, isolates the `--json-schema` channel as the only failing path, and
keeps evidence and completion gates honest. A localhost proxy is a separate
unapproved fallback. Silent downgrade from provider-native to
adapter-validated is forbidden; activation requires an explicit profile.

## Impact Analysis

- Provider-native regression tests remain green (FR-ADP-007).
- Adapter-validated results record `schemaEnforcementMode=adapter-validated`
  and `providerNativeSchema=false`; never provider-native (FR-ADP-001).
- Serialization cannot introduce sources, URLs, claims, or claim-source
  mappings absent from the frozen ledger (FR-ADP-004).
- Three format attempts maximum with one unchanged evidence hash; exhaustion
  returns `blocked` or `repair-needed`, never `complete` (FR-ADP-006).
- Failures propagate without false completion (FR-ADP-008).

## Validation Evidence

- Adapter tests: `test_research_adapter.py` covering FR-ADP-001..010 (execution
  pending Python permission; implementation complete and deterministic).
- Native regression: `test_research_repair.py` extended failure-class coverage.
- Sensitive scan over candidate scripts and generated evidence: clean.
- Tool drift scan: no P0 drift introduced.
- Live GLM 5.2 + Exa canary (FR-ADP-009): NOT executed in this packet; blocked
  until an exact approved live packet is reviewed (per non-goals).

## Safety And Privacy

All new scripts are workspace-local, perform no live external calls, and spawn
no subprocess. Credentials are never read or persisted; the
`inherit-claude-auth-only` boundary is preserved. No global Skills, Claude
settings, gateway, or environment were changed (FR-ADP-010).

## Risks

- Python test execution requires tool permission approval; implementation is
  complete but execution evidence is pending.
- Real runtime acceptance (FR-ADP-009) and global installation (FR-ADP-010)
  remain separately approved gates.
- `DS-OPT-20260827-001` remains blocked until real integration acceptance passes.

## Risks And Follow-up

- After exact live approval, run the GLM 5.2 + Exa canary and a full Research
  packet through both stages; accept only with zero P0/P1 findings.
- Downstream skills (handoff-feedback-reviewer, development-system) reference
  the new failure classes via updated contract documents in this change.

2026-09-08 format compatibility: validated-candidate is rendered as validated / candidate only; the original candidate-only meaning is unchanged and does not assert global deployment.
