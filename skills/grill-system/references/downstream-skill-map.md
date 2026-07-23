# Downstream Skill Map

Use this map after a grilling session reaches an exit criterion.

| Condition | Next skill | Output expected |
|---|---|---|
| terms or domain concepts were resolved | domain-modeling | glossary or ADR update |
| requirement decisions are stable | write-requirements-prd or to-spec | PRD/spec |
| work is ready to slice | to-tickets | tracer-bullet tickets |
| a state/UI/logic question cannot be settled in prose | prototype | throwaway answer artifact |
| a claim needs external evidence | research | cited HTML evidence report |
| execution should start | implement or ui-test | controlled implementation or test run |
| a failure needs a tight feedback loop | diagnosing-bugs | repro loop and root-cause path |
| the session is too long or branches | handoff | continuation document |
| the effort exceeds one session | wayfinder | map and investigation tickets |

## Do Not Route

- Do not route to implementation while P0 questions remain unresolved.
- Do not route to tickets when the destination itself is unclear.
- Do not route to prototype for questions that can be answered by reading existing code or docs.
- Do not route to research for decisions that belong to the user.
