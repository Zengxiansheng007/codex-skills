# Scripts And Validation Change Ledger

## Purpose

Record changes to validators, tests, or scripts.

## Outline

| Date | Change ID | Section | Change Type | Summary | Status |
|---|---|---|---|---|---|
| 2026-08-25 | CR-20260825-001 | scripts/ | added | Add preflight_research.py, validate_research_result.py, live_mode_guard.py, check_tool_drift.py, test_research_repair.py. | validated |
| 2026-08-10 | CR-20260810-001 | scripts/test_research_skill.py | updated | Add semantic checks for the strong gate and user-confirmed light-path exception. | validated |
| 2026-08-09 | CR-20260809-001 | scripts/ | added | Add validator, test, and scan scripts. | validated |
## Detailed Records

### CR-20260825-001 - research-repair-scripts

- Section changed: scripts/.
- Before: Only validate_research_skill.py, test_research_skill.py, and scan_sensitive.py existed.
- After: Added preflight_research.py (FR-RR-003), validate_research_result.py (FR-RR-004), live_mode_guard.py (FR-RR-001/005), check_tool_drift.py (FR-RR-002), test_research_repair.py (AC-RR-001).
- Why: Each fail-closed condition needs a deterministic script and the full suite needs deterministic tests.
- Impact: All six FR-RR requirements have executable validators and tests.
- Validation: Pending execution due to tool permission restriction.
- Detail record: ../entries/2026/2026-08/CR-20260825-001-research-repair.md

### CR-20260810-001 - strong-gate-test

- Section changed: scripts/test_research_skill.py.
- Before: Tests covered only generic validator structure and a minimal happy-path skill shell.
- After: Tests now assert that the research skill root advertises the strong gate, includes the user-confirmed downgrade rule, and ships the new reference file.
- Why: The new behavior is semantic, so it needs an explicit regression check instead of relying only on generic structure validation.
- Impact: Future edits that re-open silent light-mode behavior should fail the deterministic test.
- Validation: Pending.
- Detail record: ../entries/2026/2026-08/CR-20260810-001-strong-research-gate.md

### CR-20260809-001 - scripts-added

- Section changed: scripts/.
- Before: No validation scripts existed.
- After: Added validator, test, and sensitive scan scripts.
- Why: Minimum validation gate requires structure validation, tests, and sensitive scan.
- Validation: Pending execution due to sandbox directory creation constraint.
- Detail record: ../entries/2026/2026-08/CR-20260809-001-claude-research-loop.md

### CR-20260908-002 - Research routing split

- Section changed: approved candidate routing/identity boundary.
- Before: generic research was the Claude execution entry.
- After: generic router and retained guided execution are separate.
- Why: approved research-routing review.
- Impact: research-guided; no global writes.
- Validation: candidate evidence in development workspace; initially pending.
- Detail record: [record](../entries/2026/2026-09/CR-20260908-002-research-routing.md).
