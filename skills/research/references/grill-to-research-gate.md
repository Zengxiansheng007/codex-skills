# Grill To Research Gate

Use this reference when `grill-system` produces a P0/P1 question, finding, defect, or blocked decision that needs evidence before a recommendation is safe.

## Input

Accept grill findings in this shape when available:

```json
{
  "findingId": "",
  "severity": "P0 | P1 | P2",
  "question": "",
  "purpose": "",
  "blockedDecision": "",
  "evidence": [],
  "recommendedAnswer": "",
  "status": "proposed | confirmed | changed | rejected | needs-evidence"
}
```

## Workflow

1. Extract the blocked decision and the recommendation that would be affected.
2. Map the finding to required evidence types, such as primary docs, versioned docs, reference skills, reference projects, standards, or local observation.
3. Check current evidence coverage.
4. If P0/P1 coverage is `insufficient`, generate follow-up queries and run research before producing the recommendation.
5. If evidence is inaccessible or policy-blocked, return `blocked` or `partial` and list risk acceptance needs.
6. Write `grillFindingCoverage` into `research-decision-gate`.

## Recommendation Rule

Do not present a deterministic design, repair, test, or implementation recommendation for a P0/P1 grill finding unless coverage is `sufficient` or explicitly `caveated`.
