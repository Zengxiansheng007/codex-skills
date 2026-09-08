# Local Global Skill Edit Loop

Use this reference before changing a global Codex Skill under the user's Codex home directory.

## Required Pattern

1. Read the target global Skill and required references.
2. Copy or mirror the target Skill into an approved workspace path when edits are needed.
3. Capture a baseline before changes:
   - target Skill path;
   - relevant files;
   - validator and test status;
   - known change-record state.
4. Patch the workspace copy first.
5. Add or update traceable change records when the target Skill's contract requires them.
6. Validate the workspace copy.
7. Ask for explicit approval before deploying back to the global Skill directory.
8. Back up the current global Skill before deployment when practical.
9. Deploy the validated workspace copy.
10. Re-run global validation after deployment.
11. Update the change record from pending/applied to validated only after deployed validation passes.

## Mandatory Workspace-Copy-First Scope

This loop is mandatory for:

- any `global Skill edit`;
- any `multi-file change`;
- any `high-risk change`;
- any `single-file behavior change`, including changes to routing, validation, fixtures, scripts, approval gates, adapter behavior, handoff semantics, or final-state classification.

Only a single-file pure wording, formatting, comment, typo, or non-behavioral documentation cleanup may use the direct edit exception.

## Required Evidence

- baseline validation result;
- workspace validation result;
- deployment approval boundary;
- deployed global validation result;
- sensitive-data scan;
- Change ID and record paths for file-changing updates.

## Forbidden Shortcuts

- Do not edit the global Skill first and validate later.
- Do not mark completion based only on workspace validation.
- Do not skip change records for an existing Skill update unless the final state is blocked or review-required.
- Do not treat a successful copy operation as validation.

## Recovery

If global deployment fails, keep the workspace copy and report:

- what was changed;
- what did not deploy;
- backup location, if created;
- validation status of the workspace copy;
- exact approval or environment blocker.
