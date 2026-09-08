# CR-20260817-001 - CLW PH-2/PH-3/PH-4 deterministic contracts

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | development-system |
| Change Type | added / validation / governance |
| Scope | scripts-and-validation / schemas / references-and-assets |
| Source | CLW PH-2, PH-3 and PH-4 requirement anchors dated 2026-08-17 |
| Author | Codex control plane; no live Agent claim accepted |

## Summary

Added deterministic CLW queue/DAG and aggregate snapshot helpers (PH-2),
Windows isolated slot/write-set/merge-candidate gates (PH-3), and independent
Agent profile/capability/feedback review helpers (PH-4). Added schemas,
contracts and a cross-phase regression suite.

## Context And Problem

PH-2 and PH-3 had approved final requirements and plans but the workspace runtime only contained generic queue/merge helpers that did not enforce the CLW graph, stable selection, Windows path, independence or profile boundaries. PH-4 was only a high-level roadmap and had no independent anchor or machine contract. The baseline tests also depended on an expired wall-clock policy fixture.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `scripts/development_runtime.py` | CLW PH-2/3/4 helpers | Add graph, selection, aggregate snapshot, Phase completion, Windows write-set, isolated slot, merge candidate, Agent profile/match/review gates. |
| `scripts/test_clw_phase2_phase4_runtime.py` | New | Add deterministic positive and fail-closed matrix. |
| `schemas/*.schema.json` | Five CLW schemas | Add queue, aggregate snapshot, merge candidate, Agent profile and feedback review shapes. |
| `references/clw-phase*.md` | Three contracts | Separate CLW namespace and retain upstream completion gates. |
| `SKILL.md` | CLW map, references, validation | Route CLW phases without colliding with DSCR phases. |
| baseline tests | Policy time | Replace wall-clock-expiring fixtures with deterministic observation windows. |

## Decision And Alternatives

Selected additive pure functions and schemas that reuse the existing Event History, Snapshot, preauthorization, handoff and CompletionEvaluator contracts. Rejected copying Ralph/Ralphy runtimes, duplicating handoff-system schemas, bypassing the PH-1/2/3 entry gates, automatic sandbox fallback, and treating provider availability as completion.

## Gate status

The implementation is a workspace candidate only. PH-1 CompletionEvaluator is
still `requirements-review` because the GLM-5.2 provider returned
`claude-unavailable`; therefore PH-2/PH-3/PH-4 real live acceptance and
`completed` state remain blocked by the upstream phase gate.

## Impact Analysis

- Adds deterministic workspace capabilities but does not activate live orchestration.
- Strengthens test determinism and required-file validation.
- Preserves independent Skill ownership and Codex completion authority.
- Does not change the global/user-level installed Skill.

## Validation

- `test_development_runtime.py`: pass
- `test_phase_story_contract.py`: pass
- `test_full_refactor_contract.py`: pass
- `test_clw_phase2_phase4_runtime.py`: pass
- `validate_development_system.py`: pass, P0/P1/P2 = 0/0/0

## Validation Evidence

The eight specialized suites passed, the generic `create-skill` validator was rerun with required change records, all new JSON documents parsed, and sensitive patterns were scanned. PH-1 live evidence remains the existing `claude-unavailable` manifest and is not reclassified.

## Safety And Privacy

No prompt, credential, private provider output or production data is embedded in the new schemas or reports. No dependency, global configuration, user-level Skill or external system was modified.

## Risks And Follow-up

Real three-Story serial, two-slot concurrent and Midscene/other-Agent live acceptance remain blocked by the upstream CompletionEvaluator chain. PH-3 also still requires a true temporary Git worktree integration harness before its real DoD can pass.

No global Skill, user-level installation, production write, dependency
installation or live Agent call was performed.
