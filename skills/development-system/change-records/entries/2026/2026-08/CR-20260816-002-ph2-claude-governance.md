# CR-20260816-002 - PH-2 Claude External-Agent Governance

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | development-system and workspace handoff-claude-executor |
| Change Type | fixed / validation / governance |
| Scope | core-skill-md / references-and-assets / scripts-and-validation / safety-and-governance / downstream-and-handoff |
| Source | DSCR-PH-2; Claude timeout feedback FDB-DS-PH2-CLAUDE-DEV-20260816-001-TIMEOUT; Codex takeover review |
| Baseline | Workspace copies captured before HND-DS-PH2-CLAUDE-DEV-20260816-001; global Skills unchanged |
| Author | Claude Code partial implementation; Codex bounded same-Story takeover, repair, review and completion authority |
| Related Records | CR-20260816-001, CR-20260815-003 |

## Summary

Implement all six PH-2 stories with executable registry, policy lifecycle, exact approval, dry-run, Chinese status, and bounded takeover gates. Close the incomplete changes left by the authorized Claude run after its 900-second timeout.

## Context And Problem

Claude modified the two approved workspace Skill copies but timed out before returning valid structured feedback. Codex review found missing schemas, no policy expiry/hash enforcement, a literal dry-run status bypass, no enforceable cross-Story comparison, incomplete validator coverage, and a secret-pattern false positive.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| SKILL.md | PH-2 references and capability map | Link the normative governance contract and retain Codex completion authority. |
| references/claude-governance-contract.md | complete file | Define registry, lifecycle, dry-run, status, takeover and permanent manual gates. |
| schemas/claude-*.json; schemas/codex-takeover-decision.schema.json | complete files | Add strict Draft 2020-12 machine contracts. |
| scripts/development_runtime.py | PH-2 runtime and generators | Enforce availability, active identity/hash/expiry, all approval dimensions, hashed dry-run manifests, Chinese status, and bounded same-Story takeover. |
| scripts/test_development_runtime.py | PH-2 deterministic matrix | Add positive, tamper, expiry, inactive, forged dry-run, cross-Story, threshold and budget coverage. |
| scripts/validate_development_system.py | required assets and sensitive scan | Require all PH-2 artifacts and avoid the `risk-action` false positive without weakening actual key detection. |
| assets/fixtures | PH-2 positive and negative fixtures | Align generated/static fixtures to the new contracts. |
| workspace/handoff-claude-executor | docs, secret detector and tests | Align exact-match self-approval and preserve sensitive-output regression coverage. |

## Decision And Alternatives

Use task-scoped canonical policy hashes, explicit validity times, and a hashed dry-run manifest. A plain status string and prose-only approval were rejected because either could bypass the strong gate. Takeover accepts only the original cycle, Story, authorization fingerprint and evidence lineage; a permissive fallback was rejected.

## Detailed Change

The policy hash excludes only its own `policyHash` field. Network access may be an explicit empty list; missing network is invalid. Auto-approval consumes verified dry-run records, not a caller-supplied status. Invalid feedback requires the configured consecutive count. One policy separately bounds Agent rounds and Codex takeovers.

## Impact Analysis

- Exact in-scope Claude calls can be automatically approved after a verified dry-run.
- Expired, revoked, tampered, enlarged, cross-project or mismatched policies fail closed.
- A Claude timeout can be followed by one same-Story Codex takeover without granting cross-Story or installation rights.
- Existing HCE process and feedback failure contracts remain covered by 33 deterministic tests.
- No public handoff packet schema or global Skill was changed.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Specialized validator | validate_development_system.py | accepted; P0/P1/P2 = 0/0/0 | terminal output |
| Runtime matrix | test_development_runtime.py | DEVELOPMENT_RUNTIME_OK | terminal output |
| Full-refactor slice | test_full_refactor_contract.py | FULL_REFACTOR_CONTRACT_OK | terminal output |
| Legacy contracts | phase/story, Phase 1 boundary, Skill governance tests | all pass | terminal output |
| HCE regression | test_handoff_claude_executor.py | 33/33 ALL_PASS | terminal output |
| Generic Skill validation | validate_create_skill.py --require-change-records | accepted-with-constraints; P0/P1/P2 = 0/0/0 | terminal output |

## Safety And Privacy

No real credential, prompt transcript, private repository content, production data, network access, installation, or global write was introduced. Synthetic credential patterns remain runtime-constructed inside negative tests so scanners do not mistake fixtures for real secrets.

## Risks And Follow-up

PH-3 product-level live closed-loop acceptance remains out of scope. User-level installation still requires a separate explicit approval.

Refs: DSCR-PH-2, FR-TOT-009 through FR-TOT-016, AC-TOT-007 through AC-TOT-014, AC-TOT-017, AC-TOT-018.
