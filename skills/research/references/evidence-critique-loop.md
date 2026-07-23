# Evidence Critique Loop

Use this reference for `standard` and `deep` research, and for any `light` task that reveals a P0/P1 evidence gap.

## Purpose

Research is complete only after collected evidence has been reviewed for strengths, weaknesses, confidence, conflicts, and coverage. A report may stop with `partial` or `blocked`, but it must not hide open P0/P1 gaps.

## Severity

| Severity | Meaning | Required handling |
|---|---|---|
| P0 | The conclusion would be unsafe, untrustworthy, or unusable for a high-impact recommendation. | Close the gap, return `blocked`, or require explicit risk acceptance. |
| P1 | The conclusion would likely be ambiguous, stale, poorly covered, or hard to reproduce. | Close the gap before `accepted`; otherwise use `partial`, `rerun`, or `caveated` with explicit limits. |
| P2 | Improves completeness, maintainability, or confidence. | Record as evidence debt when not fixed. |
| P3 | Nice-to-have detail. | Optional. |

## Loop Steps

1. Extract key claims and recommendation candidates.
2. Assign evidence IDs to each claim.
3. Review each claim for:
   - source authority and fit to claim type;
   - directness and version applicability;
   - independence and same-source duplication;
   - reproducibility or local observability;
   - conflicts, stale facts, and inaccessible sources;
   - missing perspectives, negative evidence, and excluded sources.
4. Create `reviewFindings` for every gap.
5. For P0/P1 findings, generate targeted `followupQueries` and preferred source tiers.
6. Repeat collection and review until:
   - P0/P1 gaps are closed;
   - access, budget, or policy blocks further research;
   - the user explicitly accepts the risk.

## Stop Rules

- `complete`: all P0/P1 findings are closed or risk-accepted, and the recommendation is supported or caveated.
- `partial`: useful evidence exists, but one or more P1 gaps remain, or some branches are inaccessible.
- `blocked`: a P0 gap remains and cannot be closed safely.
- `rerun`: the main workflow should collect more evidence before using the output.

Do not use a fixed number of rounds as the main stop rule. Stop by risk, evidence fit, source repetition, budget, and user deadline.
