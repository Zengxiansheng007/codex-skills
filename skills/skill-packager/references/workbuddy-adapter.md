# WorkBuddy Adapter

## Evidence Status

WorkBuddy public specification coverage is incomplete. Use local evidence in this order:

1. WorkBuddy builtin `skill-creator` documentation and scripts.
2. User-level installed skill examples such as `flowchart-spec`.
3. Builtin skill frontmatter samples.
4. Behavior tests against user-level skills.

Builtin skill frontmatter is evidence of fields used by WorkBuddy-shipped packages, not proof that all fields have identical semantics for user-level skills.

## Frontmatter Defaults

For a migrated user-level WorkBuddy package, write only:

```yaml
---
name: skill-name
description: >-
  Trigger-rich description without angle brackets.
agent_created: true
---
```

Rules:

- `name` must match the directory.
- `name` must be lowercase hyphen-case and not exceed 40 characters.
- `description` must not contain `<` or `>`.
- `agent_created: true` is required for agent-created user skills.
- Keep unsupported or unverified fields in `AGENT_ADAPTERS.md`, not the runtime frontmatter.

## Observed But Not Automatically Written

These fields appear in builtin samples but require user-level behavior validation before writing into runtime packages:

- `allowed-tools`
- `license`
- `author`
- `version`
- `disable-model-invocation`
- `disable`
- `description_zh`
- `description_en`
- `when_to_use`

## Agents Directory

WorkBuddy has no `agents/openai.yaml` mechanism. Exclude `agents/` from the WorkBuddy runtime package. Preserve its content in adapter notes.

If Codex metadata contains invocation-control fields, do not directly map them to WorkBuddy control fields unless behavior tests prove equivalence.

## Validation

Use the packaged `workbuddy_validate` logic instead of raw `quick_validate.py` as the primary gate.

Why:

- raw `quick_validate.py` can fail on UTF-8 Chinese files under Windows default encodings;
- raw `quick_validate.py` uses regex and can misread folded YAML descriptions such as `description: >-`;
- raw `quick_validate.py` does not check `agent_created`.

Still record raw `quick_validate.py` output as supporting evidence when available.
