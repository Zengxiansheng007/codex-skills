---
name: rag-query
description: Use when querying D:/RAG for source-grounded evidence, RC status, candidate claims, conflict records, or read-only Evidence Packets with knowledge_space_id isolation.
---

# Rag Query

## Operating Rules

- Require `knowledge_space_id` for every query.
- Search only `INDEX.md`, manifest, structured JSON, evidence JSON, and governance records.
- Do not summarize blocked materials.
- Return `need-review` when evidence exists but RC is not confirmed.

## Workflow

1. Validate the requested `knowledge_space_id` against manifest and source metadata.
2. Search structured files and evidence records in `D:/RAG`.
3. Build an Evidence Packet with status, evidence refs, source refs, and blocked reason.
4. If formal use is requested and no `confirmed_active` RC exists, block the request.

## Validation

Run `python D:\RAG\scripts\validate_rag_mvp.py`.
