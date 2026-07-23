# Skill Brief Template

Use this template before writing or changing files when the user's request is vague, high-risk, or broad.

## Required Fields

| Field | Question | Completion criterion |
|---|---|---|
| Objective | What repeated task should the skill make more reliable? | One sentence that names the work. |
| Trigger wording | What would users say when they need this skill? | At least 3 realistic trigger phrases or a reason why one phrase is enough. |
| Inputs | What files, links, systems, docs, credentials, or context are needed? | Inputs are named without embedding secrets. |
| Outputs | What should the skill produce or change? | Output format and location are explicit. |
| Success criteria | How can another agent know the skill worked? | Observable validation exists. |
| Safety boundary | What must the skill refuse, avoid, or ask before doing? | High-risk actions are listed. |
| Runtime assumptions | Which tools, APIs, OS, shell, models, or plugins are required? | Unknown dependencies are marked. |

## Classification

Pick the smallest useful type:

- `steps-only`: ordered operational workflow;
- `reference-only`: reusable vocabulary, policy, or rubric;
- `mixed`: workflow plus detailed reference;
- `tool-integration`: wraps APIs, CLIs, MCP, browser, or apps;
- `asset-template`: produces artifacts from bundled templates;
- `router`: points users or agents to other skills;
- `handoff`: preserves cross-session state.

## Resource Decision

- Use `SKILL.md` for core workflow and non-negotiable rules.
- Use `references/` for long examples, schemas, rubrics, and variants.
- Use `scripts/` for deterministic parsing, validation, generation, or repeated command construction.
- Use `assets/` only for files copied or transformed into outputs.
- Do not create resource folders "just in case."
