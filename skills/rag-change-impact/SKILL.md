---
name: rag-change-impact
description: Use when a D:/RAG source file changes, a new version is provided, or the user asks what RC, tests, packets, or downstream assets may be impacted.
---

# Rag Change Impact

## Operating Rules

- Never update RC automatically from changed source material.
- Treat new source versions as candidate evidence until user review.
- Record impacted RC, conflicts, tests, packet fixtures, and downstream consumers.

## Workflow

1. Compare source identity, hash, version, and material status.
2. Identify impacted evidence, knowledge units, conflicts, RC, and downstream packets.
3. Produce a Change Impact Packet under `D:/RAG/06_governance/changes` or `D:/RAG/reports`.
4. Mark unresolved impacts as `need-review`.

## Validation

Run `python D:\RAG\scripts\validate_rag_mvp.py`.
