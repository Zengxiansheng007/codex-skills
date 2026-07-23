# Test Design Techniques

Use these techniques selectively. A technique is required only when the source material supports it.

## Functional Coverage

- main success path;
- alternate success paths;
- required field validation;
- negative and error handling;
- permission and role behavior;
- API or integration boundaries;
- data persistence and refresh behavior.

## Equivalence And Boundaries

Identify valid, invalid, empty, null, minimum, maximum, just-below, just-above, duplicate, and special-character values when source rules define a domain.

## Decision Tables

Use decision tables when multiple business conditions combine into different outcomes. Each case should point to the rule rows it covers.

## State Transitions

Use state transition coverage when the feature has statuses, workflows, approvals, lifecycle events, retries, rollback, or cancellation.

## Pairwise Or Combination Coverage

Use combination coverage when roles, configurations, device/browser, data types, feature flags, or form fields create too many full combinations.

Before generating pairwise cases:

- define parameters and values;
- list invalid value pairs and constraints;
- keep mandatory high-risk combinations even if pairwise reduction would omit them.

## Risk-Based Coverage

Increase priority when a case guards money, permissions, irreversible writes, compliance, data loss, critical workflow blocking, high user frequency, or high defect history.

## Exploratory Charters

Use exploratory charters for areas with weak evidence. Do not label them as formal deterministic cases unless evidence later confirms the expected behavior.
