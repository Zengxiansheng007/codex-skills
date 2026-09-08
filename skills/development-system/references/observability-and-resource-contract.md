# Observability And Resource Contract

Read this before displaying runtime state or enforcing execution budgets.

`status_projection` exposes only cycle, Phase, Story, Round, governed state, blocker, heartbeat, evidence references, next action and last event type. It never exposes hidden reasoning, full prompts, credentials or private transcripts.

`evaluate_resources` enforces calls, duration, tokens, cost, rate and concurrency when the active Profile policy defines them. Any exceeded dimension produces `resource-limit-reached`, writes a recoverable snapshot and prevents another call until Codex changes the governed state.

`build_audit_report` builds a minimal event and decision timeline from Event History. Reports use reason codes, traces and evidence references; they exclude prompt bodies and internal thought fields.

Trace: FR-002, FR-007, FR-027, FR-030, FR-031, FR-032, NFR-002, NFR-006, AC-015, AC-029 through AC-031.
