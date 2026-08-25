# CR-20260820-001 Skill System v4.2 Candidate

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | ui-test |

## Summary

Prepared the v4.2 candidate contracts and compatibility redirects.

## Context And Problem

The prior Skill set lacked consistent schemas, policy separation and migration outputs.

## Sections Changed

Schemas, runtime policies, metrics, migration, redirects and tests.

## Decision And Alternatives

Centralize deterministic contracts under `ui-test` instead of extending legacy roots.

## Scope

- Requirement anchor: `ART-UI-TEST-SKILL-PRD-20260820 v4.2-approved`
- Design anchor: `ART-UI-TEST-SKILL-ARCH/DEVPLAN/TESTPLAN-20260820 v2.0-review`
- Candidate root: `work/ui-test-skill-implementation-20260820-2315/candidate-skills`

## Mapped Requirements

- FR-SKL-001..008: single control plane, archived redirects, project config, packet and execution policy.
- FR-SKL-009..016, FR-SKL-030..031: checkpoint runtime boundary, module ready context, semantic POST, Midscene/Playwright responsibility split, anti-double-submit.
- FR-SKL-017, FR-SKL-021..027, FR-SKL-032..034: canonical RunResult, evidence, completion, experience, migration issue list, metrics.
- NFR-SKL-001..010 and AC-SKL-001..026 are covered by candidate validation and release review artifacts.

## Changes

- Added canonical schema registry and missing schemas for project config, execution policy, ModuleReadyContext, RunResult, experience, feedback, migration issue list and metric records.
- Changed packet validation so mixed R1/R2 test packets are valid when each step keeps its own risk and `effective_risk_level` equals the highest step risk.
- Added execution policy decisions separate from risk classification, with production/R3/API-write/secret hard blocks.
- Normalized semantic read-only POST to `body_keys`, while accepting legacy `payload_keys` only through a compatibility adapter.
- Added one-shot non-idempotent action token handling and retry phase boundaries.
- Changed artifact budget exceedance from hard fail to warning when real resources are available.
- Added ModuleReadyContext validation, redacted metric projection, negative experience blocking and machine-readable migration issue lists.
- Converted legacy `checkpoint-runtime-v1`, `ui-test-system-a2a-handoff` and `ui-test-system-checkpoint-schema` candidate copies into archived redirect shells.

## Impact Analysis

Consumers receive one canonical status and compatibility is explicit.

## Validation Evidence

- `python -m unittest discover -s tests -p 'test*.py' -v` under `ui-test`: passed.
- `python tests/run_tests.py` under `ui-test-checkpoint-runtime`: passed.
- `python -m unittest discover -s tests -p 'test*.py' -v` under `ui-test-checkpoint-schema`: passed.
- `python -m unittest discover -s tests -p 'test*.py' -v` under `ui-test-a2a-handoff`: passed.
- `python -m compileall` for updated Python scripts: passed.

## Safety And Privacy

No private payload or credential is embedded in the candidate.

## Risks And Follow-up

Installation and private UI use remain separately gated.

## Deployment Boundary

This is a workspace candidate only. It does not authorize writing to
`C:/Users/lenovo/.codex/skills`, `D:/RAG`, or any project asset.
