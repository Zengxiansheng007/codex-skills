# Question Pack: Pre Implementation

Use before an agent or developer starts implementation.

| ID | Question | Purpose | Evidence to inspect first | Recommended answer pattern | Blocking decision |
|---|---|---|---|---|---|
| PI-01 | What exact behavior will be observable when this work is done? | Prevent implementation drift. | spec, issue, current UI/API | State user-visible behavior. | done behavior |
| PI-02 | Which test seam is agreed before coding starts? | Avoid brittle tests. | existing tests, public interfaces | Pick one stable seam. | test seam |
| PI-03 | Which files or modules are likely in scope, and which are forbidden? | Bound edits. | code ownership, module map | List likely scope and no-touch areas. | edit boundary |
| PI-04 | What should the agent not do even if it seems helpful? | Prevent scope creep. | non-goals, constraints | List forbidden changes. | non-goals |
| PI-05 | What command proves the work? | Define feedback loop. | package scripts, CI docs | Name targeted and full validation commands. | validation command |
| PI-06 | What data or environment is required? | Avoid blocked execution. | env docs, fixtures, test data | Name required setup without secrets. | setup need |
| PI-07 | What should happen if validation fails? | Define repair loop. | failure taxonomy | Classify bug, asset, env, unclear requirement. | failure policy |
| PI-08 | What is the commit or delivery boundary? | Keep work reviewable. | ticket size, dependencies | Deliver a vertical slice. | delivery slice |
