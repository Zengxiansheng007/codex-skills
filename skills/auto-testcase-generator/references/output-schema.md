# Output Schema

The skill should produce three coordinated artifacts.

## Markdown Test Cases

Use [Markdown format](markdown-format.md). Markdown is for manual testers and import-friendly review.

## HTML Review Report

Include:

- scope and input inventory;
- source-oracle decisions;
- source conflicts and stale-source risks;
- module tree;
- coverage matrix;
- case status summary for incremental maintenance;
- validation command results;
- sensitive-data redaction note;
- open questions and assumptions.

Embed a JSON block when useful:

```html
<script type="application/json" id="testcase-evidence">
{
  "skill": "auto-testcase-generator",
  "status": "accepted-with-constraints",
  "validatedCommands": [],
  "openRisks": []
}
</script>
```

## JSON Trace Matrix

Top-level shape:

```json
{
  "schemaVersion": "1.0",
  "suite": {
    "title": "Example suite",
    "mode": "change-scope",
    "generatedAt": "2026-07-13T00:00:00Z"
  },
  "sources": [
    {
      "sourceId": "SRC-001",
      "type": "prd",
      "title": "PRD section",
      "version": "v1",
      "confidence": "confirmed"
    }
  ],
  "cases": [
    {
      "caseId": "TC-001",
      "title": "Create item requires name",
      "priority": "P0",
      "modulePath": ["Workspace", "Items", "Create item"],
      "caseType": "functional",
      "sourceIds": ["SRC-001"],
      "oracle": "SRC-001",
      "confidence": "confirmed",
      "changeStatus": "new",
      "steps": [
        {
          "action": "Click Create item, leave Name empty, and click Save",
          "expected": "The Name field shows a required validation message and the item is not created"
        }
      ],
      "automationCandidate": true,
      "executionStatus": "not-run"
    }
  ],
  "conflicts": [],
  "openQuestions": []
}
```

Required per case:

- `caseId`
- `title`
- `priority`: `P0`, `P1`, `P2`, or `P3`
- `modulePath`
- `sourceIds`
- `oracle`
- `confidence`
- `changeStatus`
- `steps` with `action` and `expected`

Optional but recommended:

- `risk`
- `caseType`
- `relatedModules`
- `baselineCaseId`
- `conflictIds`
- `assumptions`
- `automationCandidate`
- `executionStatus`
