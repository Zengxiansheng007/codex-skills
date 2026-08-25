# CR-20260818-002: Unified control plane and governed checkpoint runtime

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | ui-test |

## Summary

Unified the control plane and moved checkpoint execution to the governed replacement runtime.

## Context And Problem

Legacy roots duplicated ownership and allowed contract drift.

## Sections Changed

Control-plane routing, checkpoint contracts, schemas, runtime and reports.

## Decision And Alternatives

Use one normative root with archived redirects instead of synchronizing duplicate roots.
- Requirement anchor: `RA-UIT-IMPLEMENTATION-20260818-v1.0`
- Scope: workspace candidate only

## Changes

- Made `ui-test` the only normative control plane and reduced `ui-test-system` to a forwarding shell.
- Added unified packet, route, state, Problem Details, risk, config, preflight, Midscene Adapter, deterministic verifier, retry, RunResult, evidence, experience, metrics, migration, RTM, and CompletionEvaluator contracts.
- Removed historical storage-state consumption and raw URL persistence from Checkpoint Runtime.
- Added current-session `ModuleReadyContext`, semantic read-only POST matching, relative evidence references, and single/two-session promotion semantics.
- Unified execution reporting around canonical `run-result.json`.

## Impact Analysis

Legacy callers are redirected while current callers consume one packet and result model.

## Validation Evidence

See `validation/candidate-validation.json`, `validation/rtm-v1.0.json`, `validation/public-pilot-live-v5/public-pilot-summary.json`, and `validation/completion-evaluator.json` in the development workspace.

## Safety And Privacy

Credentials, live browser state and raw private URLs are not persisted.

## Risks And Follow-up

Global installation and private execution remain independently gated.

## Deployment boundary

No global Skill was installed, no D:/RAG knowledge space was written, and no private UI was executed. Those actions remain separately gated.
