# CR-20260904-002 - PyCharm Finalization Transaction V2

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | ui-test workspace candidate |
| Change Type | contract / runtime / governance / validation |
| Scope | core-skill-md / references-and-assets / scripts-and-validation / safety-and-governance / downstream-and-handoff |
| Source | approved ST-013 requirement anchor and architecture |
| Baseline | SKILL `27130cf8`; asset governance `3538e1fc`; execution contracts `65245156`; workflow contract `54214b18`; change index `a1f0ff54` on 2026-09-04 |
| Author | Codex |
| Related Records | CR-20260904-001 |

## Summary

Introduce the 2.2/ExecutionContextV3/ExecutionAttemptV2/RunResultV5 finalization family. A normal formal node now closes through content-addressed RunResult/evidence objects, one atomic commit manifest, a receipt, one terminal, PytestSessionResult and an external PyCharmAcceptanceResult. Historical 2.1/V2/V1/V4 artifacts remain byte-readable but cannot regain new execution or acceptance eligibility.

## Context And Problem

The prior success path could persist `terminal=passed` before the project finalizer completed. A later finalizer error therefore produced a nonzero PyCharm helper exit while attempt and post-run projections appeared passed. The concrete runtime trigger was also confirmed: keyword-only parameters on custom pluggy hookspec/implementations produced empty hook argnames and a real-helper `TypeError`, while direct function-call tests bypassed dispatch. RunResultV4 also carried `pycharm_integration` and `human_r2`, so a node-local business result could self-declare process and human acceptance without the original process exit.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `SKILL.md` | Project Asset Governance, Validation, Escalation | Require 2.2/V3/V2-attempt/V5, transactional finalization, SessionResult and external acceptance. |
| `references/asset-governance.md` | Execution Context Governance | Define the content-addressed commit/receipt/terminal order, failure observability, history boundary and acceptance owner. |
| `references/execution-contracts.md` | Execution Governance Separation | Separate pytest, write, finalization, session, external acceptance and completion states. |
| `references/workflow-contract.md` | Formal close-out and exit criteria | Add the non-reorderable formal close-out flow and role ownership. |
| `schemas/*v3|*v2|*v5|*finalization*|*session*|*acceptance*` | versioned contracts | Add the 2.2/V3/AttemptV2/V5/commit/receipt/session/acceptance contract family without modifying historical schemas. |
| `scripts/ui_test_core/finalization_store.py` | content-addressed store | Stage immutable JSON objects and publish one fixed commit manifest plus receipt atomically. |
| `scripts/ui_test_core/finalization_transaction.py` | transaction coordinator | Validate V5/evidence candidates, enforce idempotency, reject partial closure and prevent post-run recovery from becoming passed. |
| `scripts/ui_test_core/run_evidence_linker.py` | V5 builder/verifier | Bind transaction, session, node, context, approval, snapshot, pre-terminal events and pytest phases without PyCharm/human self-attestation. |
| `scripts/ui_test_core/pytest_runtime_plugin.py` | finalization and session lifecycle | Order commit and receipt before terminal, persist non-empty failure detail and project PytestSessionResult. |
| completion projection | external acceptance gate | Require schema/hash-valid external acceptance and zero process/session exits; RunResult alone cannot pass PyCharm or human R2. |
| focused tests | contracts, transaction, linker and plugin | Cover Schema negatives, partial writes, idempotency, tamper, legacy read-only behavior, longrepr and session/acceptance gates. |
| `change-records/*` | traceability | Register CR-20260904-002 and update impacted category ledgers. |

## Decision And Alternatives

The accepted design uses immutable content-addressed objects and a single atomic commit manifest as the only commit point. A successful receipt must exist before the unique passed terminal. Moving only the hook order, retrying after failure, writing two fixed files sequentially, or letting RunResultV4 retain acceptance authority were rejected because they do not remove split-brain completion. SQLite was not selected because the single-manifest design closes the current atomicity requirement without a database migration.

## Detailed Change

- New formal execution requires project contract 2.2, ExecutionContextV3, ExecutionAttemptV2 and RunResultV5 with `transaction-v1` capability declarations.
- RunResultV5 owns pytest phase and business write truth only. It has no `pycharm_integration`, `human_r2` or legacy layered self-attestation field.
- RunResultV5 and evidence index are canonicalized into `objects/<sha256>.json`; orphan staging or objects are not committed evidence.
- `finalization-commit.json` is the sole commit point. A successful RunFinalizationReceipt must be persisted before the plugin creates a passed terminal.
- A finalizer exception or invalid candidate produces a Schema-valid failure receipt containing only stable error code, exception class and message digest. The TestReport/TeamCity failure detail must be non-empty and redacted.
- A commit found without its same-process receipt is sealed as failed with `recovery_mode=post-run`; it cannot be upgraded to passed.
- PytestSessionResult records the final pytest exit and per-node closure. The external AcceptanceResult additionally binds the observed helper process exit and is the only owner of PyCharm/human pass fields.
- PyCharmProcessEvidence records the actual helper path/content hashes, process exit and stdout/stderr hashes without persisting raw console text. Acceptance is generated by reading the actual evidence files and validates context, approval, terminal, commit, receipt, RunResult and SessionResult links; a minimal passed dictionary cannot satisfy Completion.
- Invalid relative refs are rejected before reads or terminal writes, deployment authorization hashes are checked against their referenced evidence files, and commit/receipt crash recovery never synthesizes passed.
- Project contract 2.1, ExecutionContextV2, ExecutionAttemptV1 and RunResultV4 remain unchanged and audit-readable, but new active execution and acceptance reject them.

## Impact Analysis

New project adapters must return a V5/evidence candidate rather than writing canonical result files. Report, evidence and completion readers must follow the commit manifest and external acceptance chain. Qualification remains separate and creates neither business RunResultV5 nor finalization commit/receipt. Global installation, formal successor activation and real R2 A/B remain separately approval-gated.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Transaction, V3/V4/V5 linker and Schema contracts | focused pytest with workspace `--basetemp` | 33 passed | content addressing, partial writes, idempotency, tamper, history boundary and V5 links |
| Skill/change-record structure | `validate_create_skill.py <candidate> --require-change-records` | accepted-with-constraints; P0/P1/P2=0/0/0; exit 0 | Codex focused documentation validation on 2026-09-04 |
| Candidate sensitive scan | `scan_sensitive_assets.py .` | clear; 0 findings; exit 0 | `raw_values_persisted=false` on 2026-09-04 |
| Full ui-test runtime/plugin | governed pytest with short controlled basetemp | 436 passed, exit 0 | `evidence/ST-013-workspace-validation.json` |
| Project adapter, deployment and real helper canaries | governed pytest with actual PyCharm 2025.3 helper | 103 passed, exit 0 | failure canary plus dual-node success/Acceptance canary |
| Independent code/test review | two read-only reviewers | P0=0, P1=0 | `evidence/ST-013-workspace-validation.json` |

## Safety And Privacy

No credential, Cookie, Token, private URL, raw exception message or business value is added to reusable documentation or contracts. Failure persistence is digest-only. This record grants no authority for global installation, D-drive deployment, browser access, real UI, R2/R3, cleanup or publication.

## Risks And Follow-up

- Workspace validation is closed; keep global installation, formal deployment and real A/B outside this record's authority.
- Installation, 2.2 formal prepare/qualification/activation and real P0-A/P0-B each require their own exact authorization and hash-bound evidence.
- A nonzero session/helper exit, missing receipt, failed receipt or post-run recovery must remain non-accepted even when the business write was verified.

Refs: UIT-PYCHARM-FINALIZATION-ST013-20260904; FR-013..FR-018; AC-013..AC-019; ADR-007..ADR-010.
