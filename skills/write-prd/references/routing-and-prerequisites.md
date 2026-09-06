# Routing And Prerequisites

## Dependency Graph

```text
write-prd
  -> write-requirements-prd
       -> grill-system requirements branch when required
  -> architecture-design
  -> development-plan
  -> test-plan
```

Preferred order for full delivery:

1. Requirements document.
2. Architecture design.
3. Development plan.
4. Test plan.

Direct child invocation is allowed, but the child must still apply its input gate and the shared artifact contract.

## Input Gates

| Artifact | Required | Missing input behavior |
| --- | --- | --- |
| PRD | user idea, notes, source docs, or current PRD | ask, grill, or produce draft with visible assumptions |
| Architecture | approved or risk-accepted PRD | architecture discovery draft only |
| Development plan | PRD plus architecture | ask for architecture or explicit risk acceptance |
| Test plan | PRD plus architecture/development/API materials | strategy draft with gaps; not execution-ready |

## Mixed Requests

When a user asks for "complete plan", "full document", or similar:

- classify all requested artifacts;
- produce separate artifacts;
- maintain separate status and approval;
- create one summary only after the component artifacts exist;
- never let the summary hide open P0/P1 issues.

## Stale Source Rule

If upstream content changed after a downstream artifact was approved, route to change-impact review before continuing. Do not silently reuse stale downstream conclusions.
