# Development Integration

Use Research Skill inside development as an evidence gate, not as an executor.

| Object | Trigger | Research output | Main workflow action |
|---|---|---|---|
| Skill development | Designing triggers, safety, schemas, validation | Skill evidence report and anti-patterns | Update `SKILL.md`, references, scripts, tests |
| Demo development | Choosing public URLs, sample APIs, and demo scope | Feasibility and risk report | Build only accepted or caveated demos |
| Project development | Selecting libraries, versions, APIs, standards | Fact and version report | Apply changes through normal coding workflow |
| Test design | Needing standards, edge cases, public examples | Test strategy evidence | Add tests and traceability |
| Defect analysis | Third-party or version behavior suspected | Root-cause evidence | Classify bug vs asset vs environment |
| Asset promotion | Turning findings into long-lived docs/scripts | Freshness and acceptance report | Promote only reviewed conclusions |

Research outputs must be reviewed as `accepted`, `caveated`, `rejected`, or `rerun` before they affect long-lived assets.

## Decision Gate Consumption

When a report includes `research-decision-gate`, downstream workflows must parse it before creating or updating long-lived assets.

| Gate field | Downstream handling |
|---|---|
| `recommendationStatus=accepted` | May use the recommendation if all relevant coverage items are `sufficient`. |
| `recommendationStatus=caveated` | May use the recommendation only with visible limitations and linked evidence. |
| `recommendationStatus=rerun` | Route back to `research` with the listed gaps or queries. |
| `recommendationStatus=partial` | Do not produce a deterministic high-impact plan unless the missing evidence is out of scope or risk-accepted. |
| `recommendationStatus=blocked` | Stop and ask for evidence, access, scope reduction, or explicit risk acceptance. |
| `rerunResearchRequired=true` | Do not promote the dependent artifact until follow-up research is complete or the user accepts risk. |
| `riskAcceptanceRequired=true` | Ask the user before converting the result into a recommendation, requirement, plan, test case, or skill change. |

This gate applies to `write-requirements-prd`, `grill-system`, `analysis-skill`, `auto-testcase-generator`, and any other skill that creates high-impact recommendations from research evidence.
