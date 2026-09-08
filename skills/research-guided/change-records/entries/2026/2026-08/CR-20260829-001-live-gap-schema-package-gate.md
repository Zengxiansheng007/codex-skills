# CR-20260829-001 - Live Gap Normalization And Schema Package Acceptance Gate

| Field | Value |
|---|---|
| Status | validated / candidate only |
| Target Skill | research |
| Change Type | adapter / validation / contract |
| Scope | scripts-and-validation / downstream-and-handoff |
| Source | real-runtime-acceptance-20260829 full Research attempt |
| Baseline | CR-20260827-001 candidate workspace |

## Summary

Repair the live adapter boundary exposed by the current GLM 5.2 + Exa run. Claude
returned valid research content but used `priority` instead of the required
`severity` field in two gap objects. The adapter now maps the compatibility alias
to the normative field, preserves malformed gaps as explicit P0 blockers, and
requires a complete result with zero P0/P1 findings before the run manifest can
be marked accepted.

## Context And Problem

The live full Research attempt passed Claude availability, Exa retrieval, fresh
session, and evidence freezing, but local Schema validation rejected the package
because two returned gap objects used `priority` without `severity`. The runner
also treated a structurally valid partial result as accepted when no Schema
finding remained. Both behaviors weakened the complete Schema package contract.
The repaired run additionally exposed that Claude can report
`retrievalStatus=partial` while omitting a corresponding P0/P1 gap entry.

## Sections Changed

- `scripts/run_live_research.py`: normalize gap severity aliases and enforce the
  complete-result acceptance gate.
- `scripts/test_research_adapter.py`: cover alias normalization, fail-closed
  classification, and rejection of partial results.
- This change record: record the live failure and the repair contract.

## Decision And Alternatives

Normalize the compatible `priority` alias at the adapter boundary and retain
unknown or missing classifications as explicit P0 blockers. Add an independent
completion predicate requiring complete status, complete evidence, and zero P0/P1
findings. Dropping malformed gaps or accepting partial output was rejected because
it would hide unresolved evidence defects. Changing the provider, gateway, or
native Schema path was outside this repair.

## Root Cause And Impact

The previous conversion copied Claude's `p0p1Gaps` objects directly into the
Schema package. The local Schema requires `gaps[].severity`, while the live
response supplied `priority`. The result was correctly rejected, but the failure
was reported as an internal adapter error and the runner had no explicit guard
against treating a structurally valid partial result as accepted.

## Impact Analysis

- Valid `priority` values remain visible and become normative `severity` values.
- Missing or invalid severity cannot disappear; it remains a P0 blocker.
- Partial or unresolved Research output cannot make the run manifest pass.
- An explicit non-passed retrieval status becomes a P1 gap and requires the
  bounded reinforcement decision.
- Reinforcement round identity is carried through the ledger, result, adapter
  validation evidence, and manifest instead of being patched after execution.
- The live mode guard records the requested reinforcement count so the guard,
  result, and manifest cannot disagree about the active round.
- Provider-native behavior, public tool boundaries, and frozen evidence rules are
  unchanged.

## Validation Evidence

- Candidate adapter regression includes the new unit/contract checks.
- The repaired live flow must rerun canary and full Research with a fresh session.
- No global Skill, Claude configuration, gateway, dependency, credential, or
  production change is included.

## Safety And Privacy

The repair is limited to the candidate Research Skill and its local test/change
record files. It performs no credential reads or persistence, uses no private
sources, does not modify Claude configuration or the gateway, and does not install
dependencies or write global Skills.

## Risks And Follow-up

The adapter can still produce a blocked result when public evidence is incomplete
or Claude returns incompatible content. A fresh canary and full Research run is
required before candidate acceptance. Global installation remains a separate
approval and release operation.

## Failure And Completion Rules

- A valid `priority` value in `P0`, `P1`, or `P2` is normalized to `severity`.
- A missing or invalid classification is retained and assigned P0 so it cannot
  disappear from the package.
- `accepted` requires local validation accepted, `completionClaim=complete`,
  `evidenceComplete=true`, zero P0/P1 findings, Claude exit 0, and zero provider
  permission denials.

2026-09-08 format compatibility: validated-candidate is rendered as validated / candidate only; the original candidate-only meaning is unchanged and does not assert global deployment.
