# Research Decision Gate Contract

High-impact research reports must include a machine-readable JSON data block:

```html
<script type="application/json" id="research-decision-gate">...</script>
```

## Schema Shape

```json
{
  "schemaVersion": "1.0",
  "depth": "light | standard | deep",
  "mode": "fact-check | skill-design | product-reference | literature-review | plan-support | grill-support",
  "recommendationStatus": "accepted | caveated | rejected | rerun | partial | blocked",
  "rerunResearchRequired": false,
  "riskAcceptanceRequired": false,
  "openCriticalFindings": [],
  "coverageMatrix": [],
  "grillFindingCoverage": []
}
```

## Required Semantics

- `openCriticalFindings` contains every open P0/P1 finding.
- `coverageMatrix` contains every P0/P1 claim, recommendation, requirement, development task, test-plan item, or skill design decision that the main workflow may consume.
- `grillFindingCoverage` contains every `grill-system` P0/P1 finding used to support a recommendation.
- `rerunResearchRequired=true` when a feasible follow-up search can close P0/P1 gaps.
- `riskAcceptanceRequired=true` when a recommendation would require using insufficient or blocked evidence.

## Downstream Contract

Downstream skills must not promote a high-impact artifact when:

- `recommendationStatus` is `rerun`, `partial`, or `blocked`;
- `openCriticalFindings` contains P0/P1 items not marked `accepted-risk`;
- any P0/P1 coverage item is `insufficient` or `blocked`;
- `riskAcceptanceRequired=true` and the user has not explicitly accepted the risk.
