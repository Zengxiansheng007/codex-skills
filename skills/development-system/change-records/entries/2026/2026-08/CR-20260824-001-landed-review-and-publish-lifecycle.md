# CR-20260824-001 - Landed Review And Publish Lifecycle

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | development-system |
| Change Type | added / changed / validation / governance |
| Scope | core-skill-md / references-and-assets / scripts-and-validation / safety-and-governance |
| Source | user request and research P1 closure |
| Baseline | `development-system` source SHA recorded in `artifacts/baseline-admission-record.json` |
| Author | Codex with Claude research attempt and bounded Codex takeover |
| Related Records | `REQ-DEV-SYSTEM-RAG-PUBLISH-20260824-001`, `RES-DEV-SYSTEM-LIFECYCLE-20260824-R1-R2` |

## Summary

Add a governed post-implementation review and document publication lifecycle.

## Context And Problem

The existing lifecycle could execute and validate Stories, but it did not expose
an executable contract for comparing real implementation evidence with immutable
requirements, maintaining candidate document revisions, or separating GitHub
publish from GitBook verification.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `SKILL.md` | description, landed review, references | Route the new lifecycle and preserve RAG ownership boundaries. |
| `references/landed-review-contract.md` | new | Define drift, candidate revision and no-RC rules. |
| `references/document-manifest-contract.md` | new | Define digest, state, idempotency and rollback rules. |
| `references/publish-package-contract.md` | new | Define dry-run-first publish planning and external adapter boundary. |
| `scripts/landed_review.py` | new | Compare baseline/observed artifacts and emit deterministic evidence. |
| `scripts/document_manifest_runtime.py` | new | Validate manifest and publish state transitions. |
| `scripts/publish_package.py` | new | Enforce preflight and target/approval match before live adapter. |
| `scripts/test_*.py` | new | Add 14 focused regression cases. |

## Decision And Alternatives

- Chosen: immutable anchor plus append-only candidate revisions.
- Chosen: computed SHA-256 and independent GitHub/GitBook state.
- Rejected: direct document overwrite, automatic RC, and treating GitHub success as online completion.

## Impact Analysis

- Existing state and completion contracts remain authoritative.
- Existing `rag-intake`, `rag-schema` and `rag-governance` remain owners of RAG admission and RC rules.
- A future live adapter must verify the exact GitHub/GitBook target and return content evidence.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Development validator | `python scripts/validate_development_system.py` | passed, P0/P1/P2 = 0 | validator output |
| Existing regression | runtime/full-refactor/PH4/CLW suites | passed | command outputs |
| New landed review | `python -m unittest discover -s scripts -p 'test_landed_review.py'` | 6 passed | test file |
| New manifest runtime | `python -m unittest discover -s scripts -p 'test_document_manifest_runtime.py'` | 5 passed | test file |
| New publish planner | `python -m unittest discover -s scripts -p 'test_publish_package.py'` | 3 passed | test file |
| Sensitive scan | development validator and focused fixture | no high-confidence match | validator output |

## Safety And Privacy

The candidate contains no credential, token, cookie, private URL or production
data. External writes remain disabled in the candidate runtime. Sensitive-like
input is blocked and not echoed.

## Risks And Follow-up

- Real `D:/RAG` write still needs the user's actual knowledge-space metadata and
  material list.
- GitBook target binding and online content verification remain account-level
  gates.
- Global installation is not included in this change record.

Refs: `requirements-prd.md`, `architecture.md`, `development-plan.md`,
`test-plan.md`, `research-decision-gate.json`.
