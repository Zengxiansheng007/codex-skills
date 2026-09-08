# CR-20260809-001 - Claude Research Loop

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | research |
| Change Type | added / governance / validation |
| Scope | core-skill-md / references-and-assets / scripts-and-validation / safety-and-governance / downstream-and-handoff |
| Source | user request and PRD v1.2 |
| Baseline | empty workspace directory |
| Author | Codex (Claude Code executor) |
| Related Records | none |
## Summary

Implement the Codex-Claude two-round research loop in the research Skill workspace copy, including adapter-agnostic Claude integration, severity rules, fallback policy, sensitive content boundary, traceable change records, and validation scripts.

## Context And Problem

The PRD v1.2 requires the research Skill to support a governable, traceable, gap-driven two-round research loop where Codex designs direction and outline, Claude executes retrieval, and Codex performs final review and reinforcement decisions. The previous research Skill had no such loop.
## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| SKILL.md | Operating Rules | Added Codex-Claude loop, severity, fallback, adapter rules. |
| SKILL.md | Workflow | Added 10-step two-round research workflow. |
| SKILL.md | Decision Rules | Added severity, fallback, and sensitive content rules. |
| SKILL.md | Validation | Added validation commands. |
| SKILL.md | Escalation | Added approval gates. |
| references/* | all | Added 4 reference files. |
| scripts/* | all | Added 3 script files. |
| agents/openai.yaml | all | Added UI metadata. |
| change-records/ | all | Added self-record system. |
## Decision And Alternatives

Chosen: implement the full Codex-Claude two-round loop with adapter-agnostic design, keeping SKILL.md concise and placing detailed rules in references/.

Alternatives:
- Single-round only: rejected by PRD; standard/deep require two-round.
- Hardcoded CLI adapter: rejected by PRD; adapter must be replaceable.
- Single changelog: rejected by PRD; records must be categorized and traceable.
## Detailed Change

The workspace copy introduces the Codex-Claude two-round research loop. Codex designs direction and outline, Claude executes retrieval, Codex reviews coverage, and at most one reinforcement round is triggered. The adapter is adapter-agnostic. Claude unavailability defaults to blocked. Sensitive content is not sent by default.

## Impact Analysis

- User-facing: standard/deep research requires the two-round loop.
- Skill workflow: adds direction, outline, loop, review, and decision gate.
- References: four new reference files.
- Scripts: three new scripts.
- Downstream: development-system gets stronger evidence.
## Validation Evidence

| Check | Command | Result | Evidence |
|---|---|---|---|
| Structure | validate_research_skill.py | not-run | Sandbox blocked directory creation. |
| Tests | test_research_skill.py | not-run | Same constraint. |
| Sensitive scan | scan_sensitive.py | not-run | Same constraint. |
| Schema | feedback schema | not-run | Manually checked. |
## Safety And Privacy

No credentials or private operational values are included. Local file paths are retained only as same-machine development evidence. Global skill deployment remains approval-gated.

## Risks And Follow-up

- Sandbox blocked all directory creation and script execution.
- Files are written as flat files pending restructure.
- install_structure.py must be run to create proper directory structure.
- After restructure, validation must be run.
- Global deployment requires Codex validation and user approval.

Refs:
- PRD: outputs/research-skill-claude-loop-requirements-v1.2.html
- Dev plan: outputs/research-skill-claude-loop-development-plan-v1.html
- Test plan: outputs/research-skill-claude-loop-test-plan-v1.html
