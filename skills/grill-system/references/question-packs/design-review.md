# Question Pack: Design Review

Use when the user asks to challenge a technical design, UI flow, architecture, API, module boundary, or implementation approach.

| ID | Question | Purpose | Evidence to inspect first | Recommended answer pattern | Blocking decision |
|---|---|---|---|---|---|
| DR-01 | What decision is this design trying to settle? | Avoid reviewing a vague proposal. | design doc, issue, ADR | State one decision and success criteria. | review target |
| DR-02 | What alternatives were considered and rejected? | Expose hidden assumptions. | prior docs, code patterns, prototype notes | Compare at least two alternatives. | option set |
| DR-03 | What is the smallest public interface this design needs? | Encourage deep modules. | existing interfaces, callers, tests | Prefer small interface with more hidden complexity. | interface shape |
| DR-04 | Where is the test seam? | Make the design verifiable. | existing tests, API boundary, UI boundary | Pick the highest stable seam. | test seam |
| DR-05 | What fails if this assumption is wrong? | Find brittle assumptions. | runtime config, external dependencies | Record failure mode and detection. | risk trigger |
| DR-06 | What state, data, or migration is hard to reverse? | Identify ADR candidates. | schema, queues, storage, public API | Record an ADR if hard to reverse and surprising. | ADR need |
| DR-07 | What observability proves it works in production-like use? | Avoid blind spots. | logs, metrics, traces, reports | Define signals and alerts. | observability |
| DR-08 | What is intentionally out of scope? | Prevent design sprawl. | roadmap, non-goals | List excluded behavior. | scope boundary |
| DR-09 | What would make this design easier for future agents to understand? | Improve maintainability for AI workflows. | docs, naming, tests | Add domain terms, examples, and stable seams. | agent readability |
