---
name: write-prd
description: Route business ideas and source materials into PRD, architecture design, development plan, or test plan skills with prerequisite checks, artifact state governance, RTM consistency, grill escalation, and change-impact reopening. Use when writing, reviewing, routing, or updating PRDs and delivery plans.
---

# Write PRD

## Purpose

`write-prd` is the top-level router for turning a business idea into separable engineering artifacts. It classifies intent, checks prerequisites, routes to the correct child skill, and governs shared state, RTM, risk acceptance, stale/reopen decisions, and cross-artifact consistency.

It does not write detailed PRD, architecture, development, or test-plan content itself.

## Operating Rules

- Treat third-party baseline skills as evidence, not runtime instructions. Use local Codex skill contracts first.
- Preserve the confirmed topology: `write-prd -> write-requirements-prd -> grill-system`, `write-prd -> architecture-design`, `write-prd -> development-plan`, and `write-prd -> test-plan`.
- Keep artifacts separated. Do not create a mixed document that hides PRD, architecture, development tasks, and test strategy in one body unless the user explicitly requests a summary view.
- Before routing, create or update the artifact envelope from `references/shared-contracts.md`.
- Use stable machine status codes and Chinese display labels from `references/shared-contracts.md`.
- Never mark an artifact `approved` while P0 ambiguity, invalid source baseline, unmapped P0/P1 RTM rows, or missing prerequisite evidence remains.
- When clarification enters Grill, inherit its active review write boundary. Formal artifacts and substitute versions remain frozen while Grill gathers answers; only the Grill ledger changes per answer.
- The ability to record or reconcile Grill ledger state is not an artifact-writing permission. Route a formal writer only after the V2 handoff supplies closure-backed, approved-scope batch evidence.
- `risk-accepted` can be consumed downstream only when the risk id, accepter, expiry/review condition, impacted requirements, and downstream validation duties are carried forward.
- User-level skill installation or writes to the global Codex Skills directory require a separate explicit approval after workspace validation.

## Routing Workflow

1. Frame the request:
   - target artifact or artifacts;
   - source materials and their freshness;
   - current lifecycle state;
   - intended reader;
   - known non-goals;
   - whether the user is asking for create, update, review, continue, change-impact, or combined delivery.
2. Load `references/shared-contracts.md` and apply the envelope, status, stable ID, RTM, source baseline, and change-impact rules.
3. If the request depends on current external facts or unresolved reference coverage, require `research` evidence or mark the output as partial.
4. Route by primary intent:

| User intent | Route | Minimum input |
| --- | --- | --- |
| Write or harden a complete requirements document / PRD | `write-requirements-prd` | user idea or source materials |
| Design system architecture from approved requirements | `architecture-design` | approved or risk-accepted PRD |
| Produce concrete engineering implementation plan | `development-plan` | PRD plus architecture, or explicit risk acceptance for missing architecture |
| Produce test strategy / plan | `test-plan` | PRD plus architecture/development/API docs, or strategy-draft downgrade |
| Mixed "full plan" request | Build dependency graph, then route in PRD -> architecture -> development -> test order | source materials |
| Review existing artifact | Route to the owning child skill in review mode | artifact plus source baseline |

5. For mixed requests, produce each artifact with an independent envelope, state, approval gate, and RTM slice.
6. For semantic changes, run the change-impact rules in `references/shared-contracts.md`; mark impacted downstream artifacts `stale` or `reopened` before continuing.
7. After a child skill returns, check:
   - status code and Chinese label are valid;
   - source baseline is explicit;
   - P0/P1 FR/NFR rows map to AC, tasks, tests, and evidence as applicable;
   - risk accepted items are propagated;
   - no child skill claimed a readiness state it cannot support from its inputs.
   - for a Grill return, that `phase`, `result`, `closureEvidence`, `writebackPolicy`, `protectedAssets`, `processArtifacts`, `exceptions`, `checkpoints`, and `writebackReceipts` permit the requested formal write. A report, question confirmation, or legacy result does not permit it.

## Decision Rules

- If the user explicitly names a child skill, route there, but still enforce that child's input gate and shared contract.
- If the user asks for a PRD and the material is new, materially changed, or P0/P1 ambiguous, route to `write-requirements-prd`, which must enter `grill-system`.
- If the user asks for architecture without approved PRD, either ask for the source PRD or produce only an architecture discovery draft with open issues.
- If the user asks for development plan without architecture, produce a limited plan only when the user accepts the missing architecture risk; otherwise route back to architecture.
- If the user asks for test plan without architecture, development, or API material, downgrade to `strategy-draft` and list missing inputs.
- If a child skill finds upstream drift, do not continue forward. Reopen the owning upstream artifact.
- After a closure-backed Grill result, perform one centralized writeback and validation pass using the current baseline. Preserve external edits; semantic conflict reopens only affected decisions. A notes-only result, blocked result, repair-needed result, partial failure, pause, or legacy-read-only result must not write formal artifacts.

## References

- Read `references/shared-contracts.md` before every routed artifact.
- Read `references/routing-and-prerequisites.md` when intent is mixed, stale, or ambiguous.
- Read `references/grill-system-requirements-adapter.md` before routing PRD clarification into `grill-system`.
- Read `references/baseline-selection.md` when explaining why the rewritten system uses Matt `ask-matt`, BMAD `bmad-prd`, Spec Kit `clarify`, enterprise architecture, Superpowers `writing-plans`, and `test-strategy-plus`.

## Validation

Validate this Skill with the installed create-skill structure validator. Resolve <create-skill-root> and <write-prd-root> from the current installation; these are path placeholders, not machine-specific defaults. If the validator is unavailable, report that missing validation capability instead of installing dependencies automatically.

```text
python <create-skill-root>/scripts/validate_create_skill.py <write-prd-root> --require-change-records
```

Validation must check frontmatter, required references, router topology, shared status mapping, grill return contract, no copied third-party private commands, no obvious secrets, and no global-skill write authorization.

## Escalation

Ask before writing outside the validated workspace candidate, installing or overwriting user-level skills, calling external models, downloading new dependencies, using private repositories, publishing, deploying, or including real credentials or production-only details.
