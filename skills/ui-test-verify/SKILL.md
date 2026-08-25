---
name: ui-test-verify
description: Convert UI exploration results into deterministic Playwright verification and bounded fallback. Use when validating Midscene output, hardening recorded Playwright scripts, replacing weak locators, checking assertions, or deciding whether a UI flow can become a stable regression script.
---

# UI Test Verify

## Purpose

Prove whether an explored UI flow actually succeeded using deterministic checks and safe fallback.

## Operating Rules

- Use Playwright as verifier, not just recorder.
- Prefer role, label, placeholder with scope, stable attributes, row-scoped locators, visible dialog scope, URL, selected state, and API evidence.
- Mark weak locators: `nth()`, `rc_select_*`, dynamic ID, long CSS, absolute XPath, global duplicate text, coordinate click, and fixed sleep.
- Every UI-changing action needs a postcondition.
- Fallback must preserve original failure and mark degraded execution.
- Formal regression is one Python pytest-playwright implementation per Source Case. Do not create a parallel TypeScript implementation.
- Generate a thin test that references versioned Flow/Page/Component/action bindings. Never copy page locators into each case.
- Every formal test gets a fresh BrowserContext and executes the complete setup Flow even when Midscene used a direct module route.
- Require an `in_sync` active release and write evidence only to the Path Planner run namespace.

## Workflow

1. Read exploration output and evidence.
2. Convert successful exploration stages into deterministic Playwright functions.
3. Replace weak locators with scoped semantic or stable locators where possible.
4. Add verification after input, select, click, modal open, navigation, submit, and result display.
5. If Midscene failed, apply bounded fallback and record cause.
6. Output `next_action: evidence` or `next_action: review`.

## Validation

- Each action has a concrete verifier.
- Dynamic selectors have a fallback strategy.
- Fixed waits are replaced by condition-based waits where possible.
- The script can be run by Codex and by a tester in PyCharm when packaged for Python.

Read [the locator policy](references/locator-policy.md) before promoting generated automation.

## Safety

Verification cannot create new write authority. Require a current-run R2 approval before any visible UI submit, and block production, API business creation, second submit, and assertion weakening.
