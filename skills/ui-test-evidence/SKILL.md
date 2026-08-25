---
name: ui-test-evidence
description: Build Solution D evidence indexes for UI automation runs. Use for screenshots, JSON snapshots, API responses, contract checks, task-state polling, downstream validation, failure attribution, redaction policy, and Codex-readable evidence reports.
---

# UI Test Evidence

## Purpose

Collect and normalize evidence so humans and Codex can determine what really happened.

## Operating Rules

- Page success, API success, task success, and downstream success are different evidence layers.
- Preserve every step's evidence reference. Do not hide duplicate screenshots; mark them as repeated visual state.
- Capture screenshots for UI-changing steps and all browser-visible failures.
- Capture JSON for API, contract, task-state, downstream, and AI-vision evidence.
- Redact sensitive values unless the user explicitly states the run is public and non-sensitive.
- Consume canonical RunResult and preserve its run/case/branch/step lineage. Evidence cannot change overall status.
- Store execution evidence under the governed `D:\UI-Test` run path and only redacted evidence indexes under the configured `D:\RAG` knowledge space.
- Reject formal C-drive references and root/type mismatches; ordinary non-UI-Test workspace files are outside this rule.

## Workflow

1. Build an evidence index from run artifacts.
2. Classify each artifact by step, layer, type, timestamp, sensitivity, and consumer.
3. Attach failure attribution with layer, root cause, confidence, evidence refs, impact scope, action taken, and next step.
4. Generate Codex-readable JSON and human-readable HTML references when required.
5. Output `next_action: review`.

## Validation

- Each executed step has evidence or an explicit missing-evidence reason.
- Failure evidence is enough to distinguish business defect, test asset problem, environment-data issue, requirement ambiguity, AI recognition failure, policy block, or unknown.
- Sensitive data handling is recorded.

Read [the evidence taxonomy](references/evidence-taxonomy.md) before classifying cross-layer evidence.

## Safety

Do not persist credentials, authentication state, raw private endpoints, or unredacted business identifiers. Evidence collection cannot authorize a write or change canonical RunResult status.
