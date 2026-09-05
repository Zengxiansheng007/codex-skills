# Downstream And Handoff Change Ledger

## Purpose

Track downstream dependency, handoff boundary, phase exit and successor migration changes.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-09-04 | CR-20260904-002 | project candidate handoff, SessionResult and external AcceptanceResult | changed | Move adapter output to candidates and reserve PyCharm/human pass for an external real-exit evaluator | applied |
| 2026-09-04 | CR-20260904-001 | schema, resolver, plugin, adapter deployment and completion handoff | changed | Define the v2.1 source-to-successor flow, terminal-after V4 evidence and the later protected gates for global install, prepare, qualification, activation and human A/B PyCharm R2 | applied |

## Detailed Records

### CR-20260904-002 - pycharm-finalization-transaction-v2

- Section changed: adapter boundary, reporting handoff, rollout and human acceptance.
- Before: project finalizer wrote fixed result files and RunResult carried PyCharm/human projections.
- After: adapter returns a candidate, core commits it, session records pytest exit and an external evaluator binds the observed helper exit.
- Why: the component that creates business evidence cannot attest its own process/human acceptance.
- Impact: reports and completion must consume the commit/receipt/session/acceptance chain; rollout and real A/B remain separately approved.
- Validation: focused contract and transaction tests passed; downstream deployment and real A/B are not authorized by this record.
- Detail record: `../entries/2026/2026-09/CR-20260904-002-pycharm-finalization-transaction-v2.md`.

### CR-20260904-001 - pycharm-execution-context-v2

- Section changed: schemas, contract registry, fixtures and tests.
- Before: v2.0 project config, v1 R2 approval record and v3 RunResult were active; no execution context or attempt schema existed.
- After: five new active contracts (project v2.1, execution-context v2, execution-attempt v1, r2-approval-record v2, run-result v4) registered; three old contracts deprecated to read-only audit.
- Why: establish schema foundation for unified PyCharm execution context, per-node attempt lifecycle, separated approval-source identity and layered status before implementing runtime (PH-02) or project migration (PH-03).
- Impact: no runtime plugin, lock, attempt runtime, adapter or deployment is implemented in this change. Historical schemas, releases and RunResults remain immutable. Subsequent stories (ST-002 through ST-012) depend on these schemas.
- Validation: all validation marked not-run-by-agent; Codex must independently execute schema meta-validation, fixture validation, contract registry validation and test suite.
- Detail record: `../entries/2026/2026-09/CR-20260904-001-pycharm-execution-context-v2.md`.
