# Research HTML Contract

The runtime artifact is one self-contained HTML file.

Required data blocks:

```html
<script type="application/json" id="research-metadata">...</script>
<script type="application/json" id="evidence-index">...</script>
<script type="application/json" id="search-log">...</script>
<script type="application/json" id="run-status">...</script>
```

High-impact reports must also include:

```html
<script type="application/json" id="research-decision-gate">...</script>
```

High-impact means the output may affect a PRD, development plan, test plan, skill design, product selection, security posture, public recommendation, or a `grill-system` P0/P1 finding.

The scripts are data blocks only. Do not include executable JavaScript unless the user explicitly asks for an interactive report.

Required status values:

- `complete`: sufficient evidence for scoped question.
- `partial`: useful evidence exists but some branches are blocked, weak, or stale.
- `blocked`: cannot answer safely or reliably.

Recommended top-level sections:

1. Summary
2. Scope And Assumptions
3. Key Findings
4. Evidence Table
5. Conflicts And Uncertainty
6. Source Coverage
7. Security And Access Notes
8. Main Workflow Recommendation

The main workflow must be able to parse the file and locate all evidence from the embedded JSON.

For downstream consumption, read `research-decision-gate-contract.md`. A report with open P0/P1 evidence gaps must not use `run-status.status=complete` and `recommendationStatus=accepted` together unless those gaps are explicitly marked risk-accepted.
