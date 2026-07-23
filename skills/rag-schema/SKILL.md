---
name: rag-schema
description: Use when validating D:/RAG frontmatter, manifest files, schema-lite packet contracts, fixtures, evidence JSON, or local RAG structural integrity.
---

# Rag Schema

## Operating Rules

- Validate structure before content confidence.
- Treat `08_cache` as rebuildable and never as source of truth.
- Packet schemas are local MVP schema-lite JSON contracts until a full JSON Schema validator is introduced.

## Workflow

1. Load schemas from `D:/RAG/schemas`.
2. Validate JSON parse for all `.json` files under `D:/RAG`.
3. Validate required fields and allowed statuses for packet fixtures.
4. Confirm negative fixtures fail for the expected reason.
5. Produce a schema validation report.

## Validation

Run `python D:\RAG\scripts\validate_rag_mvp.py`.
