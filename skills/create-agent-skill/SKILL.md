---
name: create-agent-skill
description: Create or improve concise Codex agent skills from a workflow, domain requirement, SOP, tool integration, or repeated task. Use when the user asks to write, review, optimize, package, validate, or document an Agent Skill / Codex skill / SKILL.md, including deciding scripts, references, assets, metadata, trigger descriptions, progressive disclosure, examples, and validation steps.
---

# Create Agent Skill

## Operating Rules

Create skills as small operational playbooks for another Codex agent. Prefer essential procedural knowledge over broad explanations. Keep `SKILL.md` lean, and move detailed examples, scoring rubrics, or variant-specific guidance into `references/`.

Use this order:

1. Clarify the skill objective, triggers, inputs, outputs, success criteria, and safety boundaries.
2. Decide whether the skill needs only `SKILL.md` or also `references/`, `scripts/`, or `assets/`.
3. Initialize or update the skill folder.
4. Write concise frontmatter and body instructions.
5. Validate the skill structure.
6. Forward-test or simulate realistic usage when the skill is nontrivial.

## Skill Design Checklist

Before writing files, answer these questions:

- What repeated task will this skill make more reliable?
- What user wording should trigger it?
- What should the agent produce or change?
- Which steps must be followed exactly?
- Which decisions can be left to the agent?
- What external tools, APIs, credentials, files, or permissions are needed?
- What evidence proves the skill worked?
- What should the skill refuse, avoid, or ask before doing?

If the user has not chosen a location, create personal skills under `$CODEX_HOME/skills`; when unset, use `~/.codex/skills`.

## File Structure

Use the smallest structure that supports the job:

```text
skill-name/
  SKILL.md
  agents/openai.yaml
  references/
  scripts/
  assets/
```

Required:

- `SKILL.md`: YAML frontmatter plus concise Markdown instructions.

Recommended:

- `agents/openai.yaml`: UI metadata.

Optional:

- `references/`: detailed guides loaded only when needed.
- `scripts/`: deterministic commands, validators, generators, converters, or wrappers.
- `assets/`: templates, icons, sample files, or boilerplate copied into outputs.

Do not add README, changelog, installation guide, long tutorial notes, or evaluation reports unless the user explicitly asks. They create noise and are not part of the operating skill.

## Frontmatter

Use only:

```yaml
---
name: skill-name
description: What the skill does and exactly when to use it.
---
```

Rules:

- `name` must match the folder name.
- Use lowercase letters, digits, and hyphens.
- Keep the name short and action-oriented.
- Put trigger conditions in `description`, because only metadata is available before the skill loads.
- Do not rely on a body section named "When to use"; the body is loaded too late for triggering.
- Avoid extra frontmatter fields such as `version`, `tags`, `author`, `compatibility`, or nested metadata unless the local platform explicitly requires them.

## Body Pattern

Use imperative instructions. A strong `SKILL.md` body usually contains:

1. **Operating rules**: non-negotiable behavior.
2. **Workflow**: ordered steps the agent should follow.
3. **Decision rules**: when to choose scripts, references, assets, or fallback paths.
4. **Validation**: commands or checks that prove the skill is usable.
5. **Escalation and safety**: when to ask the user, avoid live changes, or protect secrets.

Prefer concrete examples and short checklists. Remove background theory unless it changes execution.

## Progressive Disclosure

Treat context as limited:

- Keep `SKILL.md` focused on the core workflow.
- Put long schemas, rubrics, examples, and provider-specific details in `references/`.
- Link each reference from `SKILL.md` and say when to read it.
- Keep references one level deep.
- Avoid duplicating the same content in `SKILL.md` and references.

Read `references/skill-quality-rubric.md` when reviewing or hardening a skill.

## Resource Selection

Choose resources by execution risk:

- Use plain instructions when the task is flexible and judgment-heavy.
- Add `references/` when the agent needs detailed domain knowledge or multiple variants.
- Add `scripts/` when the same fragile logic would otherwise be rewritten repeatedly.
- Add `assets/` when outputs need templates, sample files, icons, or boilerplate.

Scripts must be runnable and validated. If a script depends on external tools or credentials, document those assumptions in the skill body.

## Validation

After creating or changing a skill:

1. Run the local skill validator when available, for example:

```bash
python path/to/quick_validate.py path/to/skill-folder
```

2. Inspect `SKILL.md` for:
   - frontmatter has only `name` and `description`;
   - description includes use cases and trigger wording;
   - body is procedural, not a tutorial;
   - references are discoverable and not duplicated;
   - no secrets, credentials, or project-private data are embedded.

3. For nontrivial skills, forward-test with a realistic user request:

```text
Use $skill-name to complete [realistic task].
```

Do not leak the intended answer into the test prompt.

## Review Heuristics

When reviewing an existing skill, prioritize:

- trigger accuracy;
- unnecessary context or duplicated content;
- missing validation;
- brittle steps that should be scripts;
- hidden assumptions about tools, permissions, environment, or credentials;
- resources that are never referenced;
- outputs that cannot be verified.

Return findings first, then a compact change plan.
