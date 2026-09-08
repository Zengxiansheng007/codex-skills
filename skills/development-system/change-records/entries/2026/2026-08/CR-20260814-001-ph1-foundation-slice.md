# CR-20260814-001 - PH-01 Foundation Slice (ST-001 ~ ST-004)

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | development-system |
| Change Type | contract / schema / fixture / validator / test |
| Scope | core-skill-md / references-and-assets / scripts-and-validation / safety-and-governance |
| Source | DS-PSR-001 Phase 1 stories PH1-ST-001 through PH1-ST-004 |
| Baseline | existing workspace validated by `validate_development_system.py` before change |
| Author | Codex (Claude Code executor) |
| Related Records | CR-20260809-001, CR-20260809-002, CR-20260809-003 |

## Summary

Implement the PH-01 foundation slice (PH1-ST-001 ~ PH1-ST-004): concise SKILL.md routing for control plane/authority, MetaGPT role SOP, artifact lifecycle and phase/story contracts; foundational JSON Schema (draft 2020-12) for requirement anchor, artifact envelope and phase/story; positive and negative fixtures proving ownership conflicts, missing FR/AC, missing entry/exit criteria, missing evidence/testability and dependency cycles are rejected; updated validator and added phase/story test script; fixed existing tests to resolve root from `__file__` rather than cwd.

## Context And Problem

Phase 1 of the Development System refactor requires a minimal vertical governance slice: from Requirement Anchor to CompletionEvaluator, script-verifiable, without live Agents. The existing workspace had routing fixtures and boundary contracts but lacked the foundational schemas, role SOP, artifact lifecycle, phase/story contract, and negative fixtures needed to prove that bypasses are rejected.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `SKILL.md` | Non-negotiable Rules | Reworded first rule to state "Codex is the sole control plane and completion authority." |
| `SKILL.md` | References | Added four new reference links: control-plane-and-authority, metagpt-role-sop-contract, artifact-lifecycle-contract, plan-story-contract. |
| `references/control-plane-and-authority.md` | new | Authority order, independent Skill ownership table, private profiles, MetaGPT hybrid reuse classification (FR-001~005, AC-001~002). |
| `references/metagpt-role-sop-contract.md` | new | Five business roles, SOP stages, entry/exit conditions, artifacts, ownership boundaries (FR-004, FR-009, AC-004). |
| `references/artifact-lifecycle-contract.md` | new | Artifact envelope fields, traceability rule, change governance (FR-006, FR-007, FR-032, AC-003). |
| `references/plan-story-contract.md` | new | Phase and story requirements, dependency cycle rule, forward evolvability (FR-008, AC-005). |
| `schemas/requirement-anchor.schema.json` | new | JSON Schema draft 2020-12 for versioned requirement anchor. |
| `schemas/artifact-envelope.schema.json` | new | JSON Schema draft 2020-12 for artifact ownership and provenance. |
| `schemas/phase-story.schema.json` | new | JSON Schema draft 2020-12 for phase/story decomposition with dependency validation. |
| `assets/fixtures/phase-story/phase1-positive.json` | new | Positive fixture with four valid PH1 stories. |
| `assets/fixtures/negative/NEG-OWNERSHIP-001-private-profile-global-clash.json` | new | Negative fixture: private profile clashes with global same-name skill. |
| `assets/fixtures/negative/NEG-STORY-001-missing-fr-ac.json` | new | Negative fixture: story with empty FR/AC. |
| `assets/fixtures/negative/NEG-STORY-002-missing-entry-exit.json` | new | Negative fixture: phase with empty entry/exit criteria. |
| `assets/fixtures/negative/NEG-STORY-003-missing-testability-evidence.json` | new | Negative fixture: story missing testability and evidence. |
| `assets/fixtures/negative/NEG-STORY-004-dependency-cycle.json` | new | Negative fixture: three stories forming a dependency cycle. |
| `scripts/validate_development_system.py` | required files / schema checks / reference checks / fixture checks / CR checks | Added new files to REQUIRED_FILES, DEFAULT_ROOT from `__file__`, schema/reference/fixture validation logic, CR-20260814-001 index check. |
| `scripts/test_phase_story_contract.py` | new | Phase/story contract test: validates positive fixture, rejects negatives, checks schemas. |
| `scripts/test_phase1_boundary_contract.py` | root resolution | Fixed root to resolve from `__file__` instead of cwd. |
| `scripts/test_skill_governance_contract.py` | root resolution | Fixed root to resolve from `__file__` instead of cwd. |
| `change-records/index.md` | Latest Changes | Added CR-20260814-001 entry. |
| `change-records/categories/core-skill-md.md` | outline + detail | Added CR-20260814-001 row and detail. |
| `change-records/categories/references-and-assets.md` | outline + detail | Added CR-20260814-001 row and detail. |
| `change-records/categories/scripts-and-validation.md` | outline + detail | Added CR-20260814-001 row and detail. |
| `change-records/categories/safety-and-governance.md` | outline + detail | Added CR-20260814-001 row and detail. |

## Decision And Alternatives

Chosen: implement concise SKILL.md routing plus dedicated references, JSON Schema draft 2020-12 schemas, deterministic fixtures and a phase/story test script.

Alternatives considered:

- Put all contract details inline in SKILL.md: rejected because it would bloat the top-level router.
- Use JSON Schema draft-07: rejected because draft 2020-12 is the current standard and provides better `$defs` support.
- Rely on prose-only gates: rejected because the handoff packet explicitly forbids prose-only gates where script validation is possible.
- Skip negative fixtures: rejected because AC-001 and AC-005 require proof that bypasses are rejected.

## Impact Analysis

- Routing: SKILL.md now references four new contract documents that future agents must read before control plane, role, artifact or phase/story decisions.
- Execution safety: the validator now enforces schema presence, reference terms, positive fixture structure and negative fixture rejection rules.
- Traceability: every artifact must carry an envelope traceable to an anchor (AC-003); phases and stories must have entry/exit criteria and FR/AC mapping (AC-005).
- Ownership: private profiles and independent Skills have explicit boundaries; ownership conflicts are rejected (AC-001).
- Forward evolvability: schema fields and enum values are designed for extension by later phases without repurposing (NFR-007).
- Compatibility: no live adapter, third-party service, or persisted user data behavior changed.

## Validation Evidence

| Check | Command or Method | Result |
|---|---|---|
| Phase/story contract test | `python scripts/test_phase_story_contract.py` | passed, PHASE_STORY_CONTRACT_OK |
| Phase 1 boundary test | `python scripts/test_phase1_boundary_contract.py` | passed, PHASE1_BOUNDARY_CONTRACT_OK |
| Skill governance test | `python scripts/test_skill_governance_contract.py` | passed, SKILL_GOVERNANCE_CONTRACT_OK |
| development-system validator | `python scripts/validate_development_system.py` | passed, accepted |
| sensitive scan | validator secret-pattern scan | passed |

## Safety And Privacy

No credentials, tokens, cookies, private keys, or production-only secrets were added. The change was made only in the workspace copy. Global deployment remains approval-gated.

## Risks And Follow-up

- Not deployed to global Skill directory in this turn.
- Live Claude and Midscene execution were not part of this change.
- PH1-ST-005 through PH1-ST-010 remain for subsequent iterations.
