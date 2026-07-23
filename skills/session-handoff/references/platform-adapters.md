# Platform Adapter Notes

The core `session-handoff` skill is platform-neutral. It produces a validated handoff document and recovery prompt. Runtime-specific launch or installation behavior must stay outside the default workflow.

## Codex

- Default behavior: generate a Markdown handoff document and return the file path.
- Safe continuation: the next Codex task should read the handoff first, restate the objective, then continue.
- Global installation or updates to `~/.codex/skills` require explicit user approval.

## Claude Code

- Claude-specific fields such as `disable-model-invocation` are not part of the portable core skill.
- `/compact` and memory files can be complementary, but a handoff document should preserve task-specific continuity.
- Launching `claude --bg` or similar commands is an execution adapter. It requires a command preview, argument escaping, environment check, and explicit user confirmation.

## WorkBuddy

- Keep the portable skill frontmatter minimal unless WorkBuddy-specific validation proves extra fields are supported.
- User-level skill deployment should target the user's WorkBuddy skills directory only after approval.
- Validate adapted packages with the local WorkBuddy validator when available.

## Generic Agents

- Provide the recovery prompt plus the handoff path.
- If the new environment cannot access local paths, include artifact role descriptions and request the user to provide or remap files.

## Adapter Gate

Before any adapter starts another agent or writes global configuration:

1. Show the handoff path and launch command.
2. Confirm the target runtime and working directory.
3. Confirm sensitive data has been redacted.
4. Ask the user for approval.
5. Verify that the target task/session actually started.
