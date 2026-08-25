# CR-20260818-001 - Unified Packet Contract

| Field | Value |
|---|---|
| Status | applied |
| Target Skill | ui-test candidate |
| Change Type | added / changed / security / validation |
| Scope | core-skill-md, references-and-assets, scripts-and-validation, safety-and-governance |
| Source | confirmed total requirement and PH01-ST-002 takeover after Claude timeout |
| Baseline | workspace copy created from global ui-test at 2026-08-18; no global files changed |
| Author | Codex |

## Summary

Added a single versioned `ui-test-packet` Schema 2020-12, a deterministic standard-library validator, valid/invalid fixtures, tests and a discoverable SKILL entrypoint.

## Context And Problem

Legacy packet handling lacked one executable, fail-closed contract.

## Sections Changed

Packet schema, validator, fixtures, tests and core Skill routing.

## Decision And Alternatives

Adopt one versioned packet contract rather than allowing child-specific interpretation.

## Impact Analysis

This enables downstream routes to reject missing scope, unknown versions/actions, illegal risk combinations and secret-like packet data before execution. It does not implement browser execution, checkpoint recovery or report aggregation.

## Validation Evidence

Pending local test run; the Claude Attempt timed out after 900 seconds without changing files or returning feedback. Codex takeover is bounded to this Story and candidate directory.

## Safety And Privacy

No credentials, Cookie, Token, storage state, private URL, private screenshot or business data is included. R0/R1 write actions and secret-like values are fail-closed.

## Risks And Follow-up

The validator is the deterministic local gate while JSON Schema remains normative. A later Story must add the state machine and route validator without duplicating this contract.
