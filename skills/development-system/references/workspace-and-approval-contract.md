# Workspace And Approval Contract

Read this before local edits, live Agent execution, takeover or user-level installation.

## Workspace-Copy-First

Multi-file, high-risk, global Skill and single-file behavioral changes must use a controlled workspace copy. The validated workspace is the only default write boundary.

## Complete Preauthorization

Automatic approval requires an exact conservative match for workspace roots, actions, data, network, tools and timeout. An empty or missing dimension does not match. `preauthorization_matches` and `decide_execution` fail closed.

Inside a matching policy, Codex may approve Claude calls, tests, repairs and bounded takeover without another user prompt. A mismatch, new permission or changed scope returns `blocked-user-decision` or `risk-gate-required`.

User-level Skill installation is never covered by workspace preauthorization. It always requires a new explicit user approval after candidate validation.

Trace: FR-022, FR-023, FR-025, AC-011, AC-013.
