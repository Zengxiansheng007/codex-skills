# CR-20260822-008 - Pytest Marker And Environment Reference Governance

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | ui-test |
| Change Type | fixed / validation / governance |
| Scope | scripts-and-validation / safety-and-governance |
| Source | full-scope validation finding |
| Baseline | CR-20260822-007 validated candidate |
| Author | Codex |
| Related Records | CR-20260822-007 |

## Summary

Registered all generated pilot pytest markers and replaced an ambiguous sensitive-field-to-string mapping with an explicit environment-reference object.

## Context And Problem

The formal D-drive pilot collected both tests but emitted unknown-marker warnings. A whole-implementation sensitive scan also treated the environment-variable name used for the password reference as though it were a persisted credential value.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `pilot/build_tianjin_pilot.py` | pytest template | Generate a project-level `pytest.ini` with five governed markers. |
| `pilot/run_private_pilot.py` | runtime value map | Store destination names under explicit `env_ref` metadata. |
| `tests/test_sensitive_asset_scan.py` | regression fixture | Prove explicit environment references pass while literal credentials remain blocked. |
| D-drive pilot `pytest.ini` | current formal asset | Apply the same marker contract to the first pilot. |

## Decision And Alternatives

Do not weaken the credential-literal scanner with a broad uppercase-string allowlist. Make environment-reference semantics explicit in the caller instead.

## Detailed Change

The loader still reads only the four approved constants from the legacy source and injects values only into the child-process environment. The mapping now separates a sensitive source constant name from its destination environment reference. Generated tests continue to use stable marker names that are declared once at the function root.

## Impact Analysis

Manual and CI collection become warning-free. Credential values, URLs, Cookies and Tokens remain excluded from packets, reports and persisted runtime metadata.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Core and pilot tests | pytest | passed, 101 tests | candidate validation evidence |
| Formal test collection | pytest collect-only | passed, 2 tests and 0 unknown-marker warnings | PH-03 evidence |
| Sensitive data | implementation and formal pilot scans | clear, 0 findings in both scopes | PH-06 evidence |

## Safety And Privacy

No raw credential, private URL, Cookie, Token or browser state is introduced. The representation change grants no new execution permission.

## Risks And Follow-up

Private P0-A/P0-B remain blocked by test-network connectivity. Global installation remains separately approval-gated.

Refs: FR-CASE-033, FR-CASE-049, AC-CASE-026
