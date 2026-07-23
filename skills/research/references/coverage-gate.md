# Coverage Gate

Use this reference when research supports a recommendation, PRD, development plan, test plan, skill design, product selection, or other high-impact downstream artifact.

## Coverage Status

| Status | Meaning | Recommendation eligibility |
|---|---|---|
| `sufficient` | Evidence is high-confidence and directly covers the object. | May recommend `accepted`. |
| `caveated` | Evidence is usable but has clear limits, transfer risk, or unresolved P2/P3 gaps. | May recommend `caveated`; limitations must be visible. |
| `insufficient` | Evidence is missing, weak, stale, indirect, or materially incomplete. | Must set `rerunResearchRequired=true` for P0/P1 objects. |
| `blocked` | Evidence cannot be obtained safely or access is restricted. | Must set `riskAcceptanceRequired=true` or `blocked`. |

## Required Fields

Every P0/P1 claim, plan item, grill finding, or recommendation needs:

```json
{
  "objectType": "claim | requirement | development-task | test-plan-item | recommendation | skill-design-decision",
  "objectId": "",
  "coverageStatus": "sufficient | caveated | insufficient | blocked",
  "evidenceIds": [],
  "confidenceRationale": "",
  "limitations": []
}
```

## Gate Rules

- `accepted` is allowed only when all P0/P1 objects are `sufficient`.
- `caveated` is allowed when no P0/P1 object is `insufficient` or `blocked`, and all limits are explicit.
- `partial` is required when useful evidence exists but P1 coverage remains insufficient.
- `blocked` is required when a P0 object is `blocked` or cannot be researched safely.
- `rerun` is required when a feasible follow-up search can close an open P0/P1 gap.

For `light` mode, record the coverage decision in a compact form. If a P0/P1 gap appears, upgrade to `standard`.
