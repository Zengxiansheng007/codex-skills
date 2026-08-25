# Development Plan

## Target

Create a workspace Skill named `ui-test-execution-report` that generates governed UI automation execution reports using the latest A方案 layout.

## Phases

| Phase | Work | Done When |
|---|---|---|
| PH-1 | Requirement anchor and reference adaptation | Anchor and reference report exist |
| PH-2 | Skill package scaffold | `SKILL.md`, references, agents metadata, scripts, assets exist |
| PH-3 | Deterministic generator | Sample input can generate HTML and JSON artifacts |
| PH-4 | Validation | Validator reports zero P0/P1 findings |
| PH-5 | Deployment decision | If needed, user approves exact global Skill deployment |

## Architecture

- `SKILL.md`: operational playbook and safety rules.
- `references/report-contract.md`: stable report input/output contract.
- `scripts/generate_report.py`: deterministic report generator.
- `scripts/validate_execution_report_skill.py`: structure, output, and sensitive scan validator.
- `assets/sample-run.json`: safe sample input.
- `docs/requirement-anchor.json`: drift-control anchor.

## Non-Goals

- No browser execution.
- No live Claude/Midscene call in the Skill itself.
- No global installation without explicit approval.
- No production mutation.
