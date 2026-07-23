# Question Pack: Test Case Design

Use when the user asks to design test cases, UI automation flows, regression coverage, or Codex-to-Midscene execution inputs.

| ID | Question | Purpose | Evidence to inspect first | Recommended answer pattern | Blocking decision |
|---|---|---|---|---|---|
| TCD-01 | Which source should be treated as the current test oracle: live UI, code, PRD, Figma, design doc, or historical behavior? | Handle stale PRD/Figma/design documents. | document dates, release notes, current route, code ownership | Use the running product or latest approved requirement; mark conflicts as drift. | oracle source |
| TCD-02 | Which code modules are actually reachable in the current product? | Avoid testing removed modules left in the repo. | routes, menu config, feature flags, deployment config | Generate cases only for reachable modules unless migration testing is requested. | valid scope |
| TCD-03 | What business object and business ID prove the flow succeeded? | Avoid UI-only success. | API responses, DB IDs, task IDs, logs | Define the ID and extraction path. | success proof |
| TCD-04 | Which roles and permissions must be covered? | Capture access rules. | role matrix, route guards, test accounts | Include allowed, forbidden, and boundary roles. | permission coverage |
| TCD-05 | What are the minimum normal flows? | Establish smoke coverage. | user journey, analytics, support cases | Choose P0 flows with clear evidence. | smoke scope |
| TCD-06 | What abnormal inputs must be tested? | Cover validation and error handling. | field rules, API validation, error copy | Include invalid, missing, duplicate, expired, and unauthorized data. | negative scope |
| TCD-07 | Which upstream and downstream systems must be verified? | Avoid false success from UI. | API contract, task queue, callback, downstream page | Define UI/API/task/downstream evidence layers. | integration proof |
| TCD-08 | Which data can be safely created, reused, or cleaned up? | Prevent environment pollution. | test data policy, cleanup API, seed data | Define data prefix, teardown, and no-modify zones. | data strategy |
| TCD-09 | Which cases should remain exploratory and which should become regression scripts? | Avoid high-maintenance automation. | change frequency, business criticality, flakiness | Promote only stable high-value paths. | asset promotion |
| TCD-10 | What evidence must every failed case preserve? | Improve debugging. | report schema, screenshot policy, network logs | Require step screenshot, API trace, assertion, and failure category. | evidence policy |
| TCD-11 | What is the expected maintenance trigger when UI or API changes? | Control automation cost. | release cadence, component changes | Define update trigger and owner. | maintenance rule |
| TCD-12 | Which generated cases must be reviewed before execution? | Prevent unsafe agent behavior. | destructive actions, permissions, production data | Mark high-risk operations as manual approval or forbidden. | safety gate |
