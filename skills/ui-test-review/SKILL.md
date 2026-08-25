---
name: ui-test-review
description: Review UI automation execution quality after Midscene exploration, Playwright verification, and Solution D evidence collection. Use for classifying business defects versus test-asset issues, generating repair plans, deciding rerun scope, and promoting stable experience into Memory or regression scripts.
---

# UI Test Review

## Purpose

Review whether the UI automation result is trustworthy and decide what should be repaired, rerun, escalated, or promoted.

## Operating Rules

- Review both business outcome and Agent execution quality.
- Do not accept a test as passed just because Midscene or Playwright did not throw.
- Separate issue categories: business defect, test-asset issue, environment-data issue, requirement ambiguity, AI recognition failure, policy block, and unknown.
- Use root-cause-based repair. Do not repeatedly repair symptoms with new wording.
- Memory promotion requires evidence, applicability, limits, and at least one successful rerun for stable paths.
- Review canonical RunResult, Source/build fingerprints and the affected dependency closure. Do not repair generated views or thin tests directly.
- Route locator/page changes to Page/Component, navigation changes to Flow, case-intent changes to Source Case, and renderer defects to Case Compiler.
- Experience is advisory and cannot grant execution permission. Negative/quarantined/superseded experience blocks reuse in its exact scope.

## Workflow

1. Read the packet, evidence index, failure history, retry history, and fallback history.
2. Score execution quality: model latency, false positives, fallback rate, locator brittleness, assertion strength, evidence completeness, and rerun stability.
3. Classify issues and produce required fixes for steps, assertions, policy, evidence, fallback, data, or requirements.
4. Decide rerun scope: affected checkpoint, affected module, full chain, or blocked.
5. Decide whether experience can enter Memory and whether stable flow can become Playwright or Hybrid regression.
6. Output a review packet and next action.

## Validation

- Every failure or degraded result has a primary category and evidence reference.
- Repair plan does not weaken expectations.
- Rerun scope is justified by impact analysis.
- Memory entries are not created from unverified guesses.

Read [the review rubric](references/review-rubric.md) before promotion or rerun decisions.

## Safety

Review cannot grant write permission, activate experience, or weaken a failed assertion. Escalate unresolved policy, sensitive-data, production, and requirement-ambiguity findings.
