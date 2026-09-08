# Development System Router Contract

## Purpose

The router turns a user goal into a controlled requirement lifecycle. It decides which specialized skill should own each step and records why the step is safe to run.

## Input Classification

Classify each incoming task as one or more of:

- `simple-direct`: clear, low-risk, single-step work.
- `requirements-work`: PRD, scope, acceptance criteria, phase design, or RTM work.
- `research-gated`: requires current, external, unfamiliar, high-risk, or contested sources.
- `grill-gated`: contains P0/P1 ambiguity, irreversible decisions, or conflicting priorities.
- `skill-development`: creates, edits, packages, validates, or installs skills.
- `a2a-handoff`: needs another Agent to execute and return structured feedback.
- `adapter-execution`: invokes Claude Code, Midscene, or another local/external adapter.
- `feedback-review`: evaluates returned execution results against the requirement anchor.

Before execution, check `references/phase1-boundary-contract.md`. A `multi-file change`, `high-risk change`, `global Skill edit`, or `single-file behavior change` must use `workspace-copy-first`. Only single-file non-behavioral wording, formatting, comments, or typo cleanup may bypass the workspace-copy path.

## Router Decision Object

Every non-trivial route should preserve:

- `cycleId`
- `phase`
- `route`
- `reason`
- `requirementAnchorRef`
- `sourceBaselineRefs`
- `manualApprovalRequired`
- `nextExpectedArtifact`
- `stopConditions`

## Mandatory Drift Checks

Before any continuation decision, compare:

1. current action vs. original goal;
2. current action vs. approved scope;
3. current action vs. non-goals;
4. changed files or artifacts vs. FR/AC mapping;
5. Agent recommendation vs. Codex-owned risk gates.

Unmapped or conflicting actions must be marked `untracedAction` or `requirementDrift` and routed to review.

## Completion Rule

Completion is allowed only when the requirement anchor, evidence, implementation summary, validation results, and Codex completion review agree. A downstream Agent saying "done" is evidence, not final authority.
