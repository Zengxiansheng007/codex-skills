# CR-20260827-001 - Runtime Value Index And Loader

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | ui-test |
| Change Type | added / validation / governance |
| Scope | scripts-and-validation / safety-and-governance |
| Source | ST-RVI-0201 runtime value governance |
| Baseline | CR-20260825-006 validated candidate |
| Author | Codex |
| Related Records | CR-20260822-008 |

## Summary

Added fail-closed RuntimeValueLoader and CredentialIndexLoader contracts with human-maintained Hash verification, credential isolation, exploration value support, and synthetic test fixtures. The project-config adapter now binds every governed caller to separate scoped private YAML indexes.

## Context And Problem

UI-Test runtime values (base URLs, timeouts, retry counts, exploration values) were previously loaded from ad-hoc environment variables without structural validation or hash protection. Credential references needed to remain env_ref-only and never appear in logs or errors.

## Sections Changed

| File | Section | Change Summary |
|---|---|---|
| `schemas/runtime-value-index.schema.json` | new schema | Add runtime-value-index v1 JSON Schema with runtime_values, exploration_values, and manual_hash |
| `schemas/credential-index.schema.json` | new schema | Add credential-index v1 JSON Schema with credentials and manual_hash |
| `schemas/ui-test-project-v2.schema.json` | contract | Require scoped runtime and credential index references plus named `runtime_refs` for v2 projects |
| `scripts/ui_test_core/project_config.py` | adapter | Resolve the private index from project scope and never use OS environment values as authority |
| `scripts/ui_test_core/runtime_value_loader.py` | new module | Add fail-closed non-credential loader with Hash verification, exploration support and env_ref compatibility |
| `scripts/ui_test_core/credential_index_loader.py` | new module | Add private-path credential loader with Hash verification and required-key checks |
| `scripts/ui_test_core/__init__.py` | exports | Export RuntimeValueLoader functions |
| `schemas/contract-registry.json` | contracts | Register ui-test.runtime-value-index.v1 as active |
| `assets/fixtures/runtime-value-index-valid.json` | new fixture | Add synthetic valid fixture with correct manual_hash |
| `tests/fixtures_runtime_value_loader.py` | new fixtures | Add synthetic fixture helpers and hash computation |
| `tests/test_runtime_value_loader.py` | new tests | Add unit tests for valid, missing, hash drift, credential isolation, exploration, and error paths |

## Decision And Alternatives

Reuse the existing JCS wrapper (`scripts/ui_test_core/jcs.py`) and `secret_governance` scanner for consistency. Compute independent manual hashes for runtime values and credentials; neither hash includes the machine-maintained exploration partition.

## Impact Analysis

Callers can now load runtime values and credentials from separate structured, hash-verified private indexes instead of ad-hoc environment variables. Credential values are never persisted outside the private credential index or echoed. The legacy env_ref compatibility interface allows gradual migration without reading Windows environment variables as authority.

## Validation Evidence

| Check | Command or Method | Result | Evidence |
|---|---|---|---|
| Compile | python -m compileall -q scripts tests | passed | candidate validation |
| New tests | python -m pytest tests/test_runtime_value_loader.py -v | passed | ST-RVI-0201 evidence |
| Full suite | python -m pytest -q | passed | ST-RVI-0201 evidence |
| Sensitive scan | python scripts/scan_sensitive_assets.py . | clear | ST-RVI-0201 evidence |

## Safety And Privacy

No raw credential, private URL, Cookie, Token or browser state is introduced into the candidate package. Credential values are permitted only in the private credential index and are never echoed in loader errors.

## Risks And Follow-up

The formal project integration and YAML index are now part of this Story's implementation boundary; remaining work is limited to publishing the validated candidate and completing formal-asset verification.

Refs: FR-RVI-001, FR-RVI-002, FR-RVI-004, AC-RVI-002
