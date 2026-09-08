# Change Record Traceability Contract

Use this contract whenever the research skill changes an existing skill or is itself changed. A file-changing update is not complete until the change is traceable, validated, and referenced in the final response.

## When This Contract Applies

Apply when the task creates, edits, moves, deletes, or renames files in the research skill package, including:

- `SKILL.md`;
- `references/`;
- `scripts/`;
- `fixtures/`;
- `agents/openai.yaml`;
- validation, report, or delivery rules.
Do not require change records for guidance-only work where no files are changed.

## Record Artifact System

```text
change-records/
  index.md
  categories/
    core-skill-md.md
    references-and-assets.md
    scripts-and-validation.md
    safety-and-governance.md
    downstream-and-handoff.md
  entries/
    YYYY/
      YYYY-MM/
        CR-YYYYMMDD-NNN-short-title.md
```
## Required Record Updates

Every file-changing update must:

1. Capture the source baseline before edits.
2. Allocate a unique Change ID in the form `CR-YYYYMMDD-NNN`.
3. Update `change-records/index.md`.
4. Update every impacted category ledger under `change-records/categories/`.
5. Add one detail record under `change-records/entries/YYYY/YYYY-MM/`.
6. Record validation evidence, skipped validation with reasons, sensitive-data scan result, and remaining risks.
7. Reference the Change ID and record paths in the final response.
## Category Ledgers

| Category file | Use when changes affect |
|---|---|
| `core-skill-md.md` | `SKILL.md` trigger wording, operating rules, workflow, decision rules, validation, or escalation. |
| `references-and-assets.md` | `references/` or `fixtures/` content, templates, rubrics, or schemas. |
| `scripts-and-validation.md` | validators, tests, deterministic scripts, command contracts, or validation evidence. |
| `safety-and-governance.md` | approval gates, privacy boundaries, forbidden actions, governance, or sensitive-data handling. |
| `downstream-and-handoff.md` | handoff contracts, downstream skill routing, A2A packets, or feedback review boundaries. |

## Status Rules

| Status | Meaning |
|---|---|
| `proposed` | Record exists before edits are complete. |
| `applied` | Files changed, but validation is incomplete or failed. |
| `validated` | Required validation and record updates are complete. |
| `blocked` | The change or record cannot be completed safely. |
| `superseded` | A later record replaces this decision. |
| `reverted` | A later record rolls back this change. |
