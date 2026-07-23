# Agent-ready Output Schema

Use this reference when an artifact will be consumed by `development-plan`, `test-plan`, `testcase-generator`, `ui-test`, Codex orchestration, Midscene, Playwright, or Solution D.

## Purpose

`write-requirements-prd` owns the upstream requirement truth. It should produce structured Agent-ready inputs, not execute tests, generate full implementation plans, or write exhaustive test cases.

This schema turns business understanding into a stable handoff contract.

## Required Top-level Fields

| Field | Required | Severity if missing | Downstream consumer | Meaning |
|---|---|---|---|---|
| `documentType` | Yes | P0 | all | Artifact type and routing result. |
| `sourceBaseline` | Yes | P0 | all | Source docs, versions, dates, environment, branch, prototype, or URL. |
| `moduleUnderstanding` | Yes | P0 | development-plan, test-plan, ui-test | Module boundary, submodules, responsibilities, and non-goals. |
| `businessObjects` | Yes | P0 | testcase-generator, ui-test | Core objects, fields, IDs, status fields, validation rules. |
| `stateModel` | Conditional | P1 | testcase-generator, ui-test | Required when objects have lifecycle/status transitions. |
| `permissions` | Conditional | P1 | test-plan, testcase-generator, ui-test | Required when roles, menus, buttons, data scope, or backend enforcement matter. |
| `upstreamDownstream` | Yes | P0 | test-plan, ui-test | Upstream inputs, downstream verification, sync/async dependencies. |
| `evidenceContract` | Yes | P0 | ui-test, Solution D | UI/API/task/downstream/log evidence requirements. |
| `acceptanceCriteria` | Yes | P0 | test-plan, testcase-generator | Pass/fail criteria linked to requirements. |
| `riskAndSafety` | Yes | P0 | all | Forbidden actions, manual-confirm actions, data/security boundaries. |
| `handoffTargets` | Yes | P1 | all | Which downstream skill should consume which part. |
| `openQuestions` | Yes | P1 | grill-system, user | Unknowns, conflicts, and disputed assumptions. |
| `grillQuestions` | Conditional | P1 | grill-system | Required for P0/P1 disputes or decisions. |

## Schema Shape

Use this shape in HTML embedded JSON or Markdown tables:

```json
{
  "documentType": "business-prd | permission-rules | state-machine | ui-automation-requirement | dev-test-plan",
  "sourceBaseline": {
    "documents": [],
    "designs": [],
    "codeBranch": "",
    "environment": "",
    "capturedAt": ""
  },
  "moduleUnderstanding": {
    "moduleName": "",
    "moduleBoundary": "",
    "submodules": [],
    "inScope": [],
    "outOfScope": [],
    "responsibilities": [],
    "knownStaleOrOfflineModules": []
  },
  "businessObjects": [
    {
      "name": "",
      "keyFields": [],
      "businessIds": [],
      "displayFields": [],
      "validationRules": []
    }
  ],
  "stateModel": {
    "states": [],
    "transitions": [],
    "terminalStates": [],
    "asyncPollingRequired": false
  },
  "permissions": {
    "roles": [],
    "menuRules": [],
    "buttonRules": [],
    "dataScopeRules": [],
    "backendEnforcement": []
  },
  "upstreamDownstream": {
    "upstreamInputs": [],
    "currentModuleProcessing": [],
    "downstreamVerification": [],
    "syncDependencies": [],
    "asyncDependencies": [],
    "degradationWhenUnavailable": ""
  },
  "evidenceContract": {
    "uiEvidence": [],
    "apiEvidence": [],
    "taskEvidence": [],
    "downstreamEvidence": [],
    "logEvidence": [],
    "evidenceIndexRequired": true
  },
  "acceptanceCriteria": [],
  "riskAndSafety": {
    "allowedActions": [],
    "manualConfirmActions": [],
    "forbiddenActions": [],
    "sensitiveData": [],
    "externalModelBoundary": ""
  },
  "handoffTargets": {
    "developmentPlan": [],
    "testPlan": [],
    "testcaseGenerator": [],
    "uiTest": []
  },
  "openQuestions": [],
  "grillQuestions": []
}
```

## Missing Field Severity

- P0: Missing field blocks downstream Agent use or creates safety/evidence risk.
- P1: Missing field can proceed only with explicit assumption or human confirmation.
- P2: Missing field reduces maintainability but does not block the next step.

## Handoff Rules

| Content | Keep in `write-requirements-prd` | Handoff |
|---|---|---|
| Business facts, rules, AC, RTM | Yes | Downstream reads it. |
| Development phases, WBS, implementation design | Summary only | `development-plan`. |
| Test strategy, scope, entry/exit, evidence policy | Summary only | `test-plan`. |
| Detailed test steps and case tables | Candidate coverage only | `testcase-generator`. |
| Browser execution, screenshots, fallback, failure attribution | Input contract only | `ui-test`. |

## Grill Triggers

Send to `grill-system` when:

- module boundary is disputed;
- upstream/downstream responsibility is unclear;
- PRD, design, code, and runtime behavior conflict;
- evidence is insufficient to prove business success;
- automation action may be destructive or require approval;
- fallback or downgrade would weaken business verification;
- a P0/P1 field is missing and cannot be inferred safely.
