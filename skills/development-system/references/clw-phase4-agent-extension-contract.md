# CLW PH-4 Windows Agent Extension Contract

This contract is scoped to `CLW-PH-4` and must not be confused with DSCR-PH-4 installation governance.

## Boundary

- `development-system` owns routing, requirements, permissions, state transitions, gap review and completion.
- `handoff-system` remains an independent Skill and owns packet transport plus adapter-specific execution feedback.
- Midscene and later Agents are registered as versioned profiles; their implementation is not copied into `development-system`.
- The first release remains Windows-only and does not authorize global installation or production execution.

## Profile And Match

Every profile declares stable profile/Agent/adapter identities, version, capabilities, input/output schemas, allowed and forbidden actions, status mapping, and isolated completion authority. Duplicate identities, overlapping allow/deny actions or Agent completion authority fail closed.

An invocation is eligible only when required capabilities and actions match the selected profile and the existing complete preauthorization policy. Profile capability is not permission. A capability match cannot enlarge workspace, data, network, tool, credential, timeout, round or concurrency boundaries.

## Unified Feedback And Review

Adapter-specific output is mapped to the shared feedback contract with cycle/Story lineage, status and evidence references. Schema validation remains owned by the relevant independent adapter/feedback reviewer. `development-system` records gaps and decides `running`, `repair-needed`, `requirements-review` or `risk-gate-required` before the normal CompletionEvaluator.

Missing lineage/evidence, P0/P1 drift, unmapped actions or an Agent completion claim cannot produce completion. Claude PH-1/PH-2/PH-3 evidence and control gates remain unchanged.

Trace: CLW-ST-401 through CLW-ST-403; PH-4 route in `CLW-ADAPTIVE-LOOP-REQ-20260816-001`.
