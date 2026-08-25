---
name: ui-test-explore
description: Prepare and review Midscene-first UI exploration from a ui-test-packet. Use for semantic browser exploration, prompt packet shaping, weak locator discovery, visible-state observation, and preserving successful or failed exploration strategies before deterministic Playwright verification.
---

# UI Test Explore

## Purpose

Use Midscene as the first visual exploration layer and preserve what it learns for later verification.

## Operating Rules

- Midscene-first means first real UI exploration uses Midscene, not that Midscene alone proves success.
- Send only approved screenshots and visible page content to the model gateway.
- Never send credentials, cookies, tokens, hidden DOM, or private data to a model.
- Every Midscene action that claims success needs a planned deterministic verification.
- If Midscene returns `passed` but URL, selected state, input value, route, visible content, or API evidence disagrees, mark the step `degraded`.
- Consume the generated Midscene View and current Source/build fingerprints; do not maintain a separate manually edited case body.
- A ready current-session ModuleReadyContext may start exploration inside the module and prohibits repeating stable module-entry clicks. It never authorizes formal Playwright to skip login/menu Flow.
- Persist exploration output only in a governed `D:\UI-Test\_tmp` or run staging path selected by Path Planner.

## Workflow

1. Read the incoming `ui-test-packet`.
2. Convert test intent into concise Midscene prompts with operation, target, constraints, expected visible state, and forbidden actions.
3. Prefer stage-based exploration: login state, project switch, module entry, page or modal open, form recognition, form fill, submit/result.
4. Record successful strategy, failed strategy, reason, retry, and fallback candidate.
5. Output updated packet with `next_action: verify` or `next_action: review` when blocked.

## Validation

- Prompt includes target, visible anchor, allowed operation, expected state, and forbidden actions.
- Repeated failures preserve root cause and changed variable.
- Exploration does not skip deterministic verification requirements.

Read [the Midscene prompt rules](references/midscene-prompt-rules.md) before preparing model-facing operations.

## Safety

Ask before sending private-page visible content to a model or performing an R2 action. Never send credentials or hidden state, and never treat exploration output as write approval or final business proof.
