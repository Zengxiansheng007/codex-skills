# CR-20260830-001: Add scholar baseline compatibility bridge

## Summary

Add an optional, governed compatibility bridge from accepted Research packets
to the fixed `scholar-deep-research` v0.10.0 baseline. The bridge preserves
the baseline state and phase authorities and records fixture versus live
completion status explicitly.

## Context And Problem

The Research adapter could validate and freeze a result but could not drive the
baseline `research_state.py` workflow through report, export, and completion
evidence. The first closure prototype also needed stronger ledger and plan
lineage checks.

## Sections Changed

- Add `scripts/compatibility/` bridge, ledger, plan, and completion contracts.
- Add compatibility fixtures and regression tests.
- Document the bridge and fixture/live completion boundary in `SKILL.md`.

## Decision And Alternatives

Retain the governance orchestration layer and baseline capability layer as
separate authorities. The bridge calls baseline CLIs and delegates phase
mutation to `research_state.py`; it does not copy baseline algorithms or turn
web evidence into paper records.

## Impact Analysis

Accepted Research results with DOI, OpenAlex, arXiv, or PMID identity can be
mapped to baseline ingest payloads. Ordinary web evidence remains governance
evidence-only. Fixture runs cannot become product completion. Global Skill
installation remains separately approval-gated.

## Validation Evidence

- Compatibility bridge tests: `21/21` before candidate packaging.
- Fixed baseline closure fixture: Phase 0..7, report lint, BibTeX export, and
  formal Development System CompletionEvaluator passed internally.
- Real GLM 5.2 scholarly bridge: round 2 passed Research Schema and semantic
  gates; baseline integration remains subject to live evidence-plan validation.
- Sensitive scan and tool drift checks passed.

## Safety And Privacy

Only public Research evidence is allowed. No credentials, private documents,
global configuration, production data, or external publication is included.

## Risks And Follow-up

The baseline still needs dependency-complete non-regression. A real scholarly
bridge must provide evidence-backed Phase 3-6 inputs and a fresh exact run
before product completion. Recompute the candidate manifest and hash after all
candidate files are staged.

## 2026-09-08 Format Compatibility Addendum

The original record above did not declare an aggregate Status. That historical absence is preserved. The following row describes only this current formatting addendum, not the historical bridge's execution or deployment status.

| Field | Value |
|---|---|
| Status | applied / formatting addendum only |
| Related Current Change | CR-20260908-002 |
