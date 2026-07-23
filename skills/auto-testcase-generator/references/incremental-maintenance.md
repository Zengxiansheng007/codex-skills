# Incremental Maintenance

Use this reference when the user supplies existing test cases, a prior JSON trace, an Excel workbook, a Markdown baseline, or release-to-release changes.

## Baseline Handling

- Never overwrite history without preserving the old baseline path or hash.
- Identify the baseline format and import only the stable fields needed for comparison.
- Build a `caseMemory` map keyed by stable `caseId` when available, otherwise by normalized module path plus title plus main source IDs.
- Keep manual tester notes and execution history separate from generated design changes.

## Case Status

Use one of:

- `new`: behavior is new or no matching baseline case exists.
- `changed`: the purpose is still valid but steps, expected results, priority, or sources changed.
- `unchanged`: case remains valid.
- `deprecated`: feature or requirement is removed or unreachable.
- `needs-confirmation`: evidence conflicts or current behavior cannot be proven.

## Change-Scope Rules

- Do not expand a change note into full-module testing.
- Include direct regression only when the changed behavior affects adjacent modules, APIs, roles, states, data, or permissions.
- State why each regression case is included.
- Preserve unrelated baseline cases as `unchanged` unless the user asks for full cleanup.

## Output Fields

In JSON trace output, include:

- `baselineCaseId`
- `changeStatus`
- `changeReason`
- `previousSources`
- `currentSources`
- `deprecatedBy`
- `reviewRequired`

## Maintenance Review

Before delivery, report:

- number of new, changed, unchanged, deprecated, and needs-confirmation cases;
- source conflicts that changed case status;
- old cases not touched and why;
- risky gaps that need user, product, design, or development confirmation.
