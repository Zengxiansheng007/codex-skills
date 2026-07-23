# Execution Contracts

Read this reference when generating exploration steps, implementing verification/fallback, recording evidence, or classifying failures.

## Exploration Plan

Use a structure equivalent to:

```json
{
  "schemaVersion": "1.0",
  "goal": "Open a module list and verify its read-only state",
  "baseUrl": "https://example.invalid/login",
  "module": "example-module",
  "policy": {
    "readOnly": true,
    "forbiddenActions": ["create", "run", "delete", "publish", "change permissions"]
  },
  "steps": [
    {
      "id": "E01",
      "intent": "Open the target list",
      "operation": "aiTap",
      "target": "Target list menu item",
      "expectedResult": "Target list page is visible",
      "verify": {
        "urlContains": "/target/list",
        "selectedText": "Target list",
        "visibleText": ["Target list", "Refresh"]
      },
      "evidence": {
        "screenshot": "always",
        "json": true
      },
      "fallback": {
        "type": "playwright",
        "locatorSource": "stable-attribute"
      },
      "risk": "auto"
    }
  ]
}
```

Do not place real credentials, private URLs, tokens, or cookies in reusable examples.

## Deterministic Verification

Verify the consequence of an action, not the action call:

| Midscene action | Required verification |
|---|---|
| `aiInput` | Read actual input value and compare exactly |
| `aiTap` navigation | URL/route plus selected state or unique page content |
| `aiTap` submit | API response plus UI result; downstream state when applicable |
| `aiAssert` | DOM/state/API corroboration for critical pass/fail decisions |
| `aiQuery` | Validate type, scope, and expected identifying fields |
| `aiWaitFor` | Verify the terminal condition, not elapsed time |

If Midscene returns `passed` but verification fails, classify `ai-recognition`, mark the step `degraded`, execute eligible fallback, and verify again.

## Evidence Record

Every step record should expose:

```json
{
  "stepId": "E01",
  "intent": "Open target list",
  "status": "passed",
  "executor": "midscene",
  "startedAt": "ISO-8601",
  "finishedAt": "ISO-8601",
  "durationMs": 1000,
  "verification": {},
  "screenshotPath": "snapshots/E01-after.png",
  "dataPath": "snapshots/E01.json",
  "fallbackUsed": false,
  "failureLayer": null,
  "error": null
}
```

Keep a report-level evidence index so Codex can locate every artifact from one JSON file.

## Failure Taxonomy

| Layer | Meaning | Typical evidence |
|---|---|---|
| `business` | Product behavior violates a clear requirement | UI/API/downstream contradiction |
| `test-asset` | Plan, selector, wait, assertion, or fallback is wrong | error context and corrected replay |
| `environment-data` | Access, service, account, test data, reset, or network issue | HTTP errors, unavailable state, data checks |
| `requirement-ambiguity` | Expected behavior cannot be determined | conflicting or missing requirement |
| `ai-recognition` | Model missed, misread, or falsely confirmed the UI | model output versus deterministic state |
| `policy` | Action is unapproved or forbidden | safety rule and requested action |
| `unknown` | Evidence is insufficient | explicit evidence gap |

Choose one primary layer and optional contributing factors. Do not label test failures as business defects until test-asset, environment, and requirement causes have been excluded.

## Memory Record

Store:

- strategy and scope;
- preconditions and page/version clues;
- observed failure;
- root cause and repair;
- deterministic proof;
- success/failure counts;
- last verified time;
- status: `candidate`, `validated`, `deprecated`, or `blocked`.

Never store credentials, cookies, raw tokens, personal data, or unrestricted screenshots in Memory.

