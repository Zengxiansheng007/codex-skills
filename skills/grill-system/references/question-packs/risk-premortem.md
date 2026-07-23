# Question Pack: Risk Premortem

Use before launch, agent execution, production-like testing, migration, or high-impact workflow changes.

| ID | Question | Purpose | Evidence to inspect first | Recommended answer pattern | Blocking decision |
|---|---|---|---|---|---|
| RP-01 | If this fails badly, what is the most likely reason? | Surface the dominant risk. | incident history, constraints, known issues | Name one likely failure cause first. | top risk |
| RP-02 | What outcome is unacceptable even if the feature mostly works? | Define hard guardrails. | compliance, data, money, permissions | List unacceptable outcomes. | stop condition |
| RP-03 | Which dependency is least under our control? | Identify external fragility. | upstream, downstream, vendor APIs | Name dependency and fallback. | dependency risk |
| RP-04 | What data could be corrupted, leaked, duplicated, or lost? | Focus on data safety. | data flow, permissions, retention | Define data risk and mitigation. | data guardrail |
| RP-05 | What would we need to detect the failure quickly? | Define monitoring and evidence. | logs, metrics, traces, reports | Specify signal and owner. | detection plan |
| RP-06 | What is the rollback or stop plan? | Avoid irreversible execution. | deployment docs, feature flags | Define rollback trigger and action. | rollback plan |
| RP-07 | Who owns the decision to proceed? | Avoid ownerless risk. | org chart, issue owner | Name owner or require confirmation. | approval owner |
| RP-08 | What is safe to automate, and what requires human approval? | Gate Agent autonomy. | action list, permissions | Classify auto/manual/forbidden actions. | autonomy boundary |
