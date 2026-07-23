# Source Oracle Policy

Use this policy before designing formal test cases.

## Source Inventory

For each source, record:

- `sourceId`
- type: `live-page`, `release-note`, `feature-flag`, `route`, `menu-config`, `prd`, `change-note`, `figma`, `screenshot`, `api-spec`, `code`, `existing-test`, `user-confirmation`
- title or path
- version, commit, timestamp, or capture time
- owner if known
- confidence: `confirmed`, `likely`, `stale-risk`, `conflicting`, `unsupported`
- evidence summary

## Default Truth Order

1. User-confirmed current scope and explicit latest release or change note.
2. Live or test environment reachability: page, route, menu, feature flag, API availability, and visible behavior.
3. Release notes, deployment notes, migration notes, and current configuration.
4. PRD, change request, acceptance criteria, and business rules.
5. Figma, screenshots, wireframes, and design prototypes, with capture time.
6. Code implementation evidence.
7. Existing test cases and historical docs.

This order is a default. If the user names a different oracle for the task, follow it and record that decision.

## Conflict Rules

- PRD says feature exists, but live route/menu/flag makes it unreachable: mark as `needs-confirmation` or `deprecated`; do not create normal regression cases.
- Figma shows a control that PRD omits: create a clarification item unless live page or user confirmation proves it is current.
- Code contains a module but live/menu/route evidence is absent: mark as stale-code risk; use code only for implementation clues.
- Existing test case covers removed behavior: mark `deprecated` and preserve history in the trace JSON.
- API spec conflicts with observed API or release note: report the conflict and generate only cases for the confirmed current contract.
- User asks to test a stale or removed module intentionally: generate explicit downline, compatibility, or migration cases and label the purpose.

## Required Output

Every formal case must include:

- at least one `sourceId`;
- `oracle`: the source or rule used as the decision authority;
- `confidence`;
- `conflictIds` if the case depends on a disputed area;
- `assumptions` only when assumptions are clearly separated from formal evidence.
