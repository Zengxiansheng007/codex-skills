---
name: rag-downstream-handoff
description: Use when preparing read-only D:/RAG packets for auto-testcase-generator, ui-test, Solution D, or another downstream agent without executing those downstream workflows.
---

# Rag Downstream Handoff

## Operating Rules

- Produce packets only; do not run downstream tests or generators.
- Formal downstream packets require `confirmed_active` RC.
- Candidate packets must carry `need-review`, `candidate`, or `blocked` status.
- Visual evidence alone is insufficient for confirmed Solution D evidence.

## Workflow

1. Identify the target: `auto-testcase-generator`, `ui-test`, Solution D, or generic agent.
2. Load eligible Evidence Packet, RC Packet, Change Impact Packet, Test Asset Manifest, or Solution D Evidence Contract.
3. Enforce status rules and include blocked reasons.
4. Write a handoff artifact under `D:/RAG/07_handover` or return a read-only packet.

## Validation

Run `python D:\RAG\scripts\validate_rag_mvp.py`.
