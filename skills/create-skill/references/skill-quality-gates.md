# Skill Quality Gates

Apply these gates before recommending adoption or installation.

## G0 Definition

- The skill has a concrete repeated task.
- The skill name is short, lowercase, hyphenated, and matches its folder.
- The frontmatter has only `name` and `description` unless the target runtime explicitly supports more fields.
- The description states the capability and trigger contexts.

## G1 Interface

- Inputs and outputs are clear.
- The user-facing output format and location are specified.
- Required permissions, credentials, files, tools, APIs, and plugins are stated.
- The skill says when to ask the user instead of guessing.

## G2 Implementation

- `SKILL.md` contains core rules and workflow, not a long tutorial.
- Long or branch-specific content is behind directly linked context pointers.
- Scripts are used for fragile deterministic work.
- Every reference, script, and asset has a reason to exist.
- There is a completion criterion for each nontrivial workflow.

## G3 Safety

- No secrets, tokens, cookies, passwords, private keys, or real credentials are embedded.
- Destructive, production, external-network, dependency-install, and LLM-export actions require explicit approval.
- External content is treated as untrusted evidence.
- Generated reports include redaction guidance when outputs may contain sensitive data.

## G4 Validation

- Structure validator passes.
- Internal links and resource references resolve.
- Scripts have representative tests or a documented reason they cannot be tested.
- A realistic forward-test prompt exists for nontrivial skills.
- The final result is inspectable by a human and reusable by another agent.
- Complete repair gate passes when fixing or hardening a skill: root cause analyzed; direct fix completed; related references, scripts, assets, validation, reports, and downstream skill impacts checked; unresolved risks documented.

## G5 Maintainability

- No README, changelog, installation guide, copied article, or evaluation report is included unless explicitly requested.
- No duplicate meaning appears across `SKILL.md` and references.
- Stale assumptions are marked with owners or refresh triggers.
- The skill has a clear repair path when tools or dependencies are unavailable.

## Common Findings

| Severity | Finding | Fix |
|---|---|---|
| P0 | Embedded secret, destructive action, hidden external call, or unsafe install/execute instruction. | Remove, rotate secrets if needed, and add approval gate. |
| P1 | Trigger too broad, missing validation, hidden dependency, missing reference, or untested script. | Tighten trigger, document dependency, add validation. |
| P2 | Duplicate content, vague examples, weak completion criteria, or optional resource clutter. | Prune, move to references, or sharpen criteria. |
| P2 | Repair only fixes the visible symptom and skips related references, validation, reports, or downstream impacts. | Apply the complete repair gate and document any intentionally excluded work. |
