# Validation Rules

## Static Checks

- `SKILL.md` exists.
- Frontmatter contains `name` and `description`.
- Referenced local files from `SKILL.md` exist.
- No obvious secrets.
- WorkBuddy adapter package has `agent_created: true`.
- WorkBuddy adapter package excludes `agents/`.

## Hash Checks

- Every packaged file must have SHA256.
- Zip extraction must reproduce expected hashes.

## Deployment Checks

- Dry-run before real deploy.
- Backup existing destination before overwrite.
- Never write builtin WorkBuddy skills.

## Behavior Checks

For `grill-system`, verify the forward-test prompt should trigger:

- one-question-at-a-time grilling;
- no implementation before user confirms;
- reportable blocking question, evidence, recommendation, and status.
