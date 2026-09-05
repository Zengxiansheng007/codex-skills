# CR-20260825-001 - Semantic Issue Registry

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | ui-test |
| Story | ST-TOTAL-0402 |
| Requirements | FR-TOTAL-006, FR-TOTAL-007, FR-TOTAL-004 |
| Acceptance | AC-TOTAL-006, AC-TOTAL-007, AC-TOTAL-008 |
| Change Type | feature / contract / validation |
| Scope | semantic_rules.py, case_contracts.py, compiler.py, schemas, fixtures, tests |
| Source | architecture-v1.0.md §3.2, test-plan-v1.0.md TA-TOTAL-001..004 |
| Baseline | CR-20260822-011 validated candidate |
| Author | Claude Code (Codex executor) |
| Related Records | CR-20260822-002, CR-20260822-011 |

## Summary

Implemented the Semantic Rule Registry and stable machine-readable Issue List that runs after structural schema validation and before Case IR lowering. Blocks P0/P1 business-fact errors: wrong A/B content-component variant, popup-version assertion mismatch, missing P0 primary responsibility, R2 one-submit boundary violations, missing shared-data index_ref, and `<br>` parameter aggregation.

## Context And Problem

JSON Schema could only validate structure, not cross-field business facts. A system-announcement case (branch A) could accidentally use a rich-text component, or a homepage-popup case (branch B) could assert plain-content matches. P0 cases could lack primary responsibility. Parameters could be aggregated with `<br>`, hiding multiple facts in one node.

## Detailed Change

- Added `scripts/ui_test_core/semantic_rules.py` with 7 rule functions covering:
  - SEM-SCOPE-001: scope consistency (function and module_path)
  - SEM-VARIANT-001/002: A/B content-component variant (plain-content vs rich-content)
  - SEM-ASSERT-001/002: assertion target mismatch (popup-version in A, plain-content in B)
  - SEM-P0-001: P0 responsibility coverage
  - SEM-R2-001/002/003: R2 ui_only, one-submit boundary, environment allowlist
  - SEM-DATA-001: shared-data/public-data index_ref presence
  - SEM-ATOM-001: `<br>` parameter aggregation detection
- Each issue includes: issue_id, rule_id, severity, case_id, branch_id, source_path, message, expected, actual, suggested_fix, blocking, evidence_refs
- Issues are stably sorted by (severity_order, case_id, branch_id, rule_id, source_path, issue_id)
- Wired `validate_semantics()` into `lower_to_case_ir()` to run before IR lowering; blocking issues raise ValueError
- Updated `case_contracts.py` to export `validate_semantics` and accept `source_path` kwarg
- Updated `__init__.py` to export `validate_semantics`
- Added `schemas/semantic-issue.schema.json` (Draft 2020-12)
- Updated `schemas/source-case.schema.json` to add `public-data` to source_type enum
- Updated `compiler.py` `_render_parameter_cell` to use `; ` instead of `<br>` for joining multiple parameters
- Added `tests/fixtures_semantic.py` with 8 synthetic fixtures (2 positive, 6 negative)
- Added `tests/test_semantic_rules.py` with 16 test cases covering all rules, issue schema, stable sorting, and lowering integration

## Validation Evidence

| Check | Result |
|---|---|
| Semantic rule registry contains all required rule IDs | pass |
| Positive A (plain) fixture: 0 blocking issues | pass |
| Positive B (rich) fixture: 0 blocking issues | pass |
| A with rich-content component: blocked by SEM-VARIANT-001 | pass |
| A with popup-version assertion: blocked by SEM-ASSERT-001 | pass |
| B with plain-content component: blocked by SEM-VARIANT-001 | pass |
| Missing P0 responsibility: blocked by SEM-P0-001 | pass |
| Missing shared-data index_ref: blocked by SEM-DATA-001 | pass |
| `<br>` parameter aggregation: blocked by SEM-ATOM-001 | pass |
| R2 multi-submit: blocked by SEM-R2-002 | pass |
| Every issue has all 12 required keys | pass |
| Issue list is stably sorted | pass |
| Valid A lowers to IR without error | pass |
| Valid B lowers to IR without error | pass |
| A rich-content blocks lowering | pass |
| Missing P0 blocks lowering | pass |
| `<br>` aggregation blocks lowering | pass |
| Existing BOPS-ANNOUNCEMENT-P0-A still lowers | pass |

## Safety And Privacy

All fixtures use synthetic public data only. No credentials, cookies, tokens, private URLs, or browser state. The change does not grant new UI execution or write permissions. No D-drive writes. No global Skill modifications. No dependency installations.

## Boundary

No product aggregate renderer, XMind desktop operation, dependency installation, D-drive write, global Skill modification, private UI execution, production operation, or historical asset migration is included. ST-TOTAL-0403 (aggregate renderer) is explicitly out of scope.

## Risks And Follow-up

- The rule registry is extensible; new rules can be added by appending to RULE_REGISTRY
- Branch-component mapping is defined in BRANCH_COMPONENT_MAP and can be extended for new products
- The `<br>` rendering fix in compiler.py changes human view output format; existing golden fixtures may need re-baseline in ST-TOTAL-0403
- Product aggregate renderer (ST-TOTAL-0403) will consume the same Case IR and parameter atomization

## Sections Changed

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.

## Decision And Alternatives

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.

## Impact Analysis

Historical compatibility note: this section was added by the candidate package governance repair without changing the original business facts.
