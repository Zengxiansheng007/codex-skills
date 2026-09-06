# CR-20260829-004 - Write PRD Router Trigger Wording

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | write-prd |
| Change Type | trigger wording / governance |
| Scope | core-skill-md / safety-and-governance |
| Source | DS-OPT-20260827-001, DS-OPT-ST-005 |
| Baseline | candidate package before ST-005 audit |

## Summary

Make the router description explicitly discoverable for writing, reviewing,
routing, and updating PRDs and delivery plans.

## Context And Problem

The router performed the intended dispatch but its frontmatter lacked explicit
trigger wording required by the generic Skill validator.

## Sections Changed

- Added a `Use when` trigger sentence to SKILL.md frontmatter.
- Added this change-record ledger and detail record.

## Decision And Alternatives

Keep routing behavior unchanged and improve only discoverability metadata.
Duplicating child-skill instructions in the description was rejected.

## Impact Analysis

Trigger matching is clearer while the existing routing topology and gates stay
unchanged.

## Validation Evidence

Generic Skill validation must report zero P0/P1/P2 findings before packaging.

## Safety And Privacy

Candidate-only metadata and documentation changes; no network, credentials, or
global writes.

## Risks And Follow-up

Re-run the router and generic Skill validators after future description edits.
