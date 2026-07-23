---
name: rag-intake
description: Use when admitting user-provided files into D:/RAG, checking a material list, running sensitive prechecks, or producing admission/reject reports for the local RAG knowledge base.
---

# Rag Intake

## Operating Rules

- Only read files explicitly provided by the user or listed in `D:/RAG/00_inbox/candidate-materials.json`.
- Do not scan directories to discover new materials.
- Run sensitive precheck before content extraction.
- Do not echo matched sensitive values in reports.
- Block materials with credential, token, cookie, or unredacted production/customer-data shapes.

## Workflow

1. Load `D:/RAG/manifest.json` and `D:/RAG/00_inbox/candidate-materials.json`.
2. Verify path, material ID, status, hash when available, and `knowledge_space_id` metadata.
3. Run format identification and no-value sensitive precheck.
4. Write an admission or reject report under `D:/RAG/reports`.
5. Set candidate status only; never create RC.

## Validation

Run `python D:\RAG\scripts\validate_rag_mvp.py`.
