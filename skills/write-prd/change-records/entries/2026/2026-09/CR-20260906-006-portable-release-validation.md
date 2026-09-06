# CR-20260906-006 - Portable release validation guidance

| Field | Value |
| --- | --- |
| Status | validated |
| Target Skill | write-prd |
| Change Type | documentation / portability |
| Scope | core-skill-md / scripts-and-validation / safety-and-governance |
| Source | User request to install the validated candidate globally and publish it to GitHub |
| Baseline | Accepted phase-boundary candidate; original frozen copy preserved |
| Author | Codex |

## Summary

Replace host-specific paths in the global-write boundary and validation example with a portable installation-aware description.

## Context And Problem

The candidate carried a validation command tied to a local workspace that is not part of the published package. A public installation could not use it.

## Sections Changed

| File | Section | Change Summary |
| --- | --- | --- |
| SKILL.md | Operating Rules / Validation | Generic global Skills directory; explicit installed create-skill validator path placeholders |

## Decision And Alternatives

Keep the existing validation contract and use the already established create-skill validator when available. Do not publish a non-existent per-machine script path or install dependencies implicitly.

## Impact Analysis

Documentation/portability only. Routing, requirements ownership, phase gates, schemas, code and tests are unchanged.

## Validation Evidence

The release preflight passed for all four Skill structure/change-record checks; file hashes and source-delta checks bind the portable package. Installation performs deployed tests and hash checks; GitHub publication verifies remote content. Actual operation receipts remain task-local rather than embedding private workstation paths in this public record.

## Safety And Privacy

No credentials, private URLs or machine-specific personal paths are added. Source payload excludes bytecode/cache and private task evidence.

## Risks And Follow-up

The create-skill validator is an explicit optional installed validation tool, not a bundled dependency. Missing tooling must be reported. Runtime/host limitations from CR-20260906-005 remain unchanged.
