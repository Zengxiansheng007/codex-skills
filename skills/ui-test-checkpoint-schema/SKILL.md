---
name: ui-test-checkpoint-schema
description: Validate, bundle, and review UI-test checkpoint schema artifacts for staged exploration and reusable regression promotion. Use for stage 2.2 checkpoint packets, CP0-CP6 granularity, checkpoint evidence readiness, staleness policy, promotion gates, and checkpoint bundle validation.
---

# UI-Test Checkpoint Schema

## Purpose

This skill packages the stage 2.2 checkpoint schema contract. It validates checkpoint artifacts, builds checkpoint bundles, and decides whether a UI flow segment can be reused without repeating earlier Midscene exploration.

## Operating Rules

- Checkpoint granularity is business-subchain level, not individual click/input level.
- Use CP0-CP6 as the default stage set: governance baseline, login state, project switch, module entry, page/modal open, form fill, submit/result verification.
- Preserve dependencies between checkpoints.
- A checkpoint is reusable only when validation, evidence, governance, promotion gate, and staleness policy are satisfied.
- Write checkpoints require cleanup policy and explicit safety approval.
- Failed, degraded, or blocked checkpoints require failure attribution.

## Workflow

1. Read [references/schema.md](references/schema.md).
2. Validate checkpoint JSON against `schema/checkpoint_schema.json`.
3. Build a checkpoint bundle when all required fields pass.
4. Return invalid fields and missing governance evidence when validation fails.
5. Output downstream views for `ui_test_packet`, `handoff_packet`, `artifact_refs`, and `rag_packet` when available.

## Scripts

Use the bundled [checkpoint schema script](scripts/checkpoint_schema.py) for deterministic validation:

```powershell
python .\scripts\checkpoint_schema.py validate --input .\fixtures\checkpoint_samples_valid.json
python .\scripts\checkpoint_schema.py bundle --input .\fixtures\checkpoint_samples_valid.json --output checkpoint_bundle.json
python -m unittest discover -s tests
```

## Validation

- Schema validation passes for valid fixtures.
- Invalid fixtures fail with specific error messages.
- Bundles preserve source checkpoint ID, schema version, dependencies, evidence references, and promotion status.

## Safety

Schema validation grants no execution permission. Block write-capable checkpoint reuse, credential or browser-state persistence, and promotion without the owning `ui-test` review and approval gates.
