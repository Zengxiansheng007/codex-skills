---
name: rag-governance
description: Use when deciding whether material can become RC, recording confirmed_active decisions, reviewing conflicts, handling active/uncertain/deprecated/superseded states, or auditing local RAG governance.
---

# Rag Governance

## Operating Rules

- Only the user can confirm RC.
- `active-candidate`, `active`, and `uncertain` cannot be formal downstream truth.
- Conflicts create `CONFLICT-*` records and block RC until resolved.
- New source versions create change-impact records; they do not rewrite RC automatically.

## Workflow

1. Load candidate material and governance records.
2. Check source status, evidence refs, conflict refs, and user decision evidence.
3. Return one of: `confirmed_active`, `need-review`, `conflict`, `blocked`, `unknown`.
4. If the user confirms a decision, record it as a governance artifact with source and evidence refs.

## Validation

Run `python D:\RAG\scripts\validate_rag_mvp.py`.
