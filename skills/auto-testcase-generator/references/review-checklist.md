# Review Checklist

Use this before delivery.

## Source And Scope

- All sources have IDs, type, version or timestamp, and confidence.
- Source conflicts are explicit.
- Stale PRD, stale Figma, stale code, and unreachable modules are marked.
- Full-scope and change-scope boundaries are not mixed.

## Case Quality

- Every formal case has at least one source ID.
- Every case belongs to a real lowest-level module.
- Cross-module and end-to-end cases name the primary triggering module.
- Priority is justified by risk or scope.
- Each step has a concrete action and expected result.
- No unproven UI control, field, status, role, API, or business rule appears as a formal expectation.

## Maintenance

- Existing baseline cases are classified as new, changed, unchanged, deprecated, or needs-confirmation.
- Deprecated cases are not silently deleted.
- Duplicate cases are merged or explained.
- Direct regression has a reason tied to the change.

## Safety

- No credentials, tokens, cookies, customer data, private account data, or production-only commands are present.
- Browser, network, external LLM, dependency install, private repo, and production operations are approval-gated.

## Validation

- Markdown and JSON agree on case IDs.
- The validator has been run when artifacts exist.
- Validation failures are fixed or listed as open risks.
- HTML report records validation result and open questions.
