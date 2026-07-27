# Strict Closure Contract

Use this reference for high-impact `standard` and `deep` reports, and for any report with `research-metadata.highImpact=true` or `research-metadata.strictLoopRequired=true`.

The reusable schema lives at `assets/strict-closure.schema.json`; the runtime validators enforce the same required fields and cross-reference rules.

## Required Blocks

High-impact reports must include these JSON blocks in addition to the base report blocks:

- `critique-loop-log`
- `source-review-findings`
- `followup-query-matrix`
- `p0p1-closure-matrix`
- `research-decision-gate`

## Semantics

- `critique-loop-log` records every research round, the reviewed findings, generated follow-up queries, and stop decision.
- `source-review-findings` records weaknesses in sources, reference skills, projects, products, papers, standards, or evidence coverage.
- `followup-query-matrix` maps P0/P1 findings to targeted follow-up queries and preferred source tiers.
- `p0p1-closure-matrix` records whether each P0/P1 finding is `closed`, `blocked`, or `accepted-risk`, plus closing evidence and closure reason.

## Closure Rules

- Every P0/P1 source-review finding must have a closure entry.
- A `closed` P0/P1 finding must reference `closingEvidenceIds`.
- A non-blocked P0/P1 finding must have at least one follow-up query before closure.
- `accepted` and `caveated` recommendations must not rely on implicit closure prose only.
- `blocked` or `accepted-risk` findings must explain the reason and downstream limitation.
