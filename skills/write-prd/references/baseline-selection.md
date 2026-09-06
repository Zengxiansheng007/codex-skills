# Baseline Selection

These baselines are evidence for the rewritten local skills. They are not runtime dependencies.

| Local target | Primary baseline | Adapted value |
| --- | --- | --- |
| `write-prd` | Matt Pocock `ask-matt` | lightweight routing, context hygiene, phase boundaries |
| `write-requirements-prd` | BMAD `bmad-prd` | PRD spine, stable requirement IDs, reviewer gate, assumptions and addendum discipline |
| PRD ambiguity control | Spec Kit `clarify` plus local `grill-system` | coverage taxonomy, one-question loop, materiality filter |
| `architecture-design` | `enterprise-architecture-skill` | C4/arc42/MADR, stable architecture IDs, quality attribute review |
| `development-plan` | Superpowers `writing-plans` | precise file/interface/task planning, test-first steps, no placeholders |
| `test-plan` | `awesome-qa-skills/test-strategy-plus` | risk-driven strategy, gates, owners, assumptions, gaps |

Rejected transfer:

- third-party project commands, script runtimes, private paths, URLs, account names, personnel, or thresholds;
- fixed single-flow assumptions that conflict with direct child invocation;
- hidden external writes or model calls;
- local templates that invent facts.

Spec Kit `clarify` remains a reference only for question classification, one-question interaction, and materiality filtering. Its incremental per-question merge, save, and validation behavior is excluded because it conflicts with the Grill phase boundary and centralized post-closure writeback.
