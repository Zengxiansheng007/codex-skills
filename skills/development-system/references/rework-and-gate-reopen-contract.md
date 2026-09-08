# Rework And Gate Reopen Contract

Read this when QA, an executor, a validator or Codex finds a defect.

## Owner Routing

| Defect domain | Artifact Owner |
| --- | --- |
| requirement | `product-requirement` |
| architecture | `architect` |
| plan | `project-planner` |
| implementation | `engineer` |
| test or evidence | `qa` |
| handoff interface | `handoff-system-interface` |
| cross-domain risk | `codex-risk-gate` |

Use `route_rework`. Unknown domains enter `requirements-review`.

## Reopen Rule

The owner updates the source Artifact and increments its version. Codex computes downstream impact from `sourceAnchorId`, `sourceAnchorVersion`, `mappedFrAc` and `sourceRefs`; every affected downstream gate returns to pending. Unaffected phases and stories keep their state. Cross-domain risk requires a risk gate rather than ordinary repair.

No Agent may reopen, skip or close a gate on its own.

Trace: FR-012, FR-028, FR-032, AC-007, AC-020.
