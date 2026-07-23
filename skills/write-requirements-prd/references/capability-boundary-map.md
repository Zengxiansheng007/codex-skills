# Capability Boundary Map

Use this reference when deciding whether a capability belongs in `write-requirements-prd` or should be handed to another skill.

## Boundary Principle

`write-requirements-prd` should own the upstream truth and handoff contract. It should not absorb downstream execution, detailed implementation, exhaustive test case design, or UI automation.

## Keep in write-requirements-prd

| Capability | Keep | Reason |
|---|---|---|
| PRD drafting and review | Yes | Core repeated task. |
| Business rule extraction | Yes | Requirement truth. |
| Permission matrix normalization | Yes | Business rule and testability source. |
| State machine normalization | Yes | Business lifecycle source. |
| Business object and field extraction | Yes | Required by all downstream skills. |
| Acceptance criteria | Yes | Requirement completion boundary. |
| DoR / DoD | Yes | Readiness and done gates. |
| RTM | Yes | Cross-artifact traceability. |
| Agent-ready schema | Yes | Handoff contract. |
| Open questions and grill questions | Yes | Prevents unsafe assumptions. |

## Handoff to development-plan

| Capability | Handoff reason |
|---|---|
| Architecture and module implementation design | Implementation layer. |
| WBS and engineering task breakdown | Development execution. |
| API/data/config/migration implementation plan | Code/system change. |
| Release and rollback plan | Delivery management. |
| Engineering validation commands | Implementation verification. |

## Handoff to test-plan

| Capability | Handoff reason |
|---|---|
| Test strategy and levels | Test management. |
| Test scope and non-scope | Test planning. |
| Environment, data, entry/exit, pause/resume | Test readiness/control. |
| Defect triage and regression strategy | Test governance. |
| Evidence policy details | Test reporting/control. |

## Handoff to testcase-generator

| Capability | Handoff reason |
|---|---|
| Detailed normal/abnormal/boundary test cases | Case design. |
| Step-by-step test data and expected result tables | Case execution input. |
| Coverage matrix by rule/state/role | Detailed test inventory. |
| Automation candidate labels | Feeds execution skills. |

## Handoff to ui-test

| Capability | Handoff reason |
|---|---|
| explore-steps generation and repair | UI execution planning. |
| Midscene-first exploration | Browser execution. |
| Playwright deterministic verification and fallback | Execution reliability. |
| Screenshots, trace, API capture, evidence index | Runtime evidence. |
| Failure attribution and Agent quality report | Execution diagnosis. |
| Memory promotion and regression script stabilization | Runtime learning/regression. |

## Split Decision Checklist

Ask:

1. Is this about what the business needs and how it is accepted? Keep in `write-requirements-prd`.
2. Is this about how to build or ship it? Handoff to `development-plan`.
3. Is this about how to organize testing? Handoff to `test-plan`.
4. Is this about detailed test cases? Handoff to `testcase-generator`.
5. Is this about browser execution and evidence? Handoff to `ui-test`.

If a capability appears in multiple skills, keep only a summary in the upstream skill and put executable detail in the downstream owner.
