---
name: rag-system
description: Use when the user asks to use the local D:/RAG knowledge base, query RC/evidence, ingest user-provided materials, prepare downstream packets for auto-testcase-generator/ui-test/Solution D, validate RAG governance, or route to rag-* child skills.
---

# Rag System

## Operating Rules

- Treat `D:/RAG` as a controlled local evidence store, not a free disk search surface.
- Read only user-listed files or files already registered in `D:/RAG/00_inbox/candidate-materials.json`.
- Do not ingest secrets, credentials, tokens, cookies, or unredacted production/customer data.
- Never promote `active-candidate`, `active`, `uncertain`, or `conflict` material to formal RC.
- Formal downstream answers require `confirmed_active` RC or an explicit user decision recorded in governance.
- Do not execute `ui-test`, create formal test cases, or write downstream systems from this skill. Produce read-only packets only.

## Workflow

1. Read [references/routing-policy.md](references/routing-policy.md) for the current request type.
2. Load `D:/RAG/manifest.json` and verify the request has a known `knowledge_space_id`.
3. If the request is ingestion or file admission, hand off to `rag-intake`.
4. If the request is schema, packet, or fixture validation, hand off to `rag-schema`.
5. If the request is RC, conflict, or confirmation governance, hand off to `rag-governance`.
6. If the request is evidence lookup or citation preparation, hand off to `rag-query`.
7. If the request is source-version or impact analysis, hand off to `rag-change-impact`.
8. If the request is for `auto-testcase-generator`, `ui-test`, or Solution D, hand off to `rag-downstream-handoff`.
9. Return a concise result with status, evidence refs, blocked reasons, and next required user decisions.

## Decision Rules

- Missing or mismatched `knowledge_space_id`: stop before reading material content.
- Registered `blocked-pending-sensitive-review`: refuse ingestion, summary, RC, and downstream use.
- Registered `active-candidate`: allow candidate packets and review notes only.
- Conflicts: return `need-review` and link the conflict record.
- Requests to scan a directory: require a user-provided file list first.

## Validation

Run:

```powershell
python D:\RAG\scripts\validate_rag_mvp.py
python C:\Users\lenovo\.codex\skills\rag-system\scripts\forward_test_rag_system.py
```

Also validate this skill folder with the local skill validator when available.

## Safety

Stop and explain the blocked reason if a request would expose sensitive data, read unlisted files, use `active` as RC, cross a knowledge space boundary, or perform downstream execution.
