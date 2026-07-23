# Skill Quality Rubric

Use this rubric when reviewing or hardening a Codex skill.

## Triggering

- The `description` names both capability and use cases.
- Trigger wording includes the phrases users are likely to say.
- The skill does not depend on body text for trigger conditions.
- The skill name is short, lowercase, hyphenated, and matches the folder.

## Context Efficiency

- `SKILL.md` contains only core workflow and decision rules.
- Long examples, schemas, and variant details live in `references/`.
- References are directly linked from `SKILL.md`.
- No README, changelog, tutorial, copied article, or unrelated notes are present.
- No content is duplicated across `SKILL.md` and references.

## Execution Reliability

- Fragile repeated logic is implemented as a script or explicit command.
- Required tools, credentials, file locations, and permissions are stated.
- The workflow tells the agent what to verify before declaring success.
- Failure paths and fallback behavior are documented.

## Safety

- The skill avoids embedding secrets, account data, tokens, or private URLs.
- Destructive or live-system actions require explicit user approval.
- Outputs that may contain sensitive data include redaction guidance.
- External network or filesystem assumptions are explicit.

## Validation

- `quick_validate.py` or an equivalent structural validator passes.
- At least one realistic forward-test prompt exists for nontrivial skills.
- Scripts, if present, have been executed on representative inputs.
- The final result is inspectable by a human and usable by another agent.

## Common Defects

- Extra YAML fields that the local runtime ignores or rejects.
- A long background tutorial instead of a procedure.
- Vague trigger descriptions such as "helps with documents".
- Resource folders created "just in case".
- Hidden dependencies on a specific shell, browser, MCP server, or API key.
- No clear success criteria.
- No validation command.
