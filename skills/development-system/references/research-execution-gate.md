# Research Execution Gate

## Research Routing Compatibility

Generic research routes through the new research router. The Claude-specific gates below apply only when research-guided actually selects Claude. Explicit user-selected Codex uses its host evidence contract without fabricated Claude/MCP fields. AnySearch uses its guarded router boundary; non-quota faults pause all dependent work, with zero retry and manual resume. A routed handoff or paused task is never completion. Original guided quality and failure checks remain required for their own profile.


Use this gate whenever `development-system` routes a Story through the
`research` Skill and Claude Code public retrieval.

## Required preflight

The research adapter must prove, before live retrieval:

- live mode is not `plan`;
- the Claude session is fresh;
- MCP schema is visible and the tool count is greater than zero;
- requested tools exactly match the public-research registry;
- the Exa canary passed with zero permission denials;
- the result will be validated as pure UTF-8 JSON against the research schema.

Missing or failed preflight is `blocked-external-dependency` or
`repair-needed`, never `completed`.

## Completion rule

`development-system` may accept a research result only after the research
validator passes, source mappings and verification status are complete, and
Codex reviews the evidence. A plan, a live process, a JSON-shaped response,
or a Claude completion claim is not completion evidence by itself.

## Failure propagation

Research failure classes are downstream evidence. `plan-mode-blocked`, tool
scope mismatch, missing MCP schema, stale session, failed canary, permission
denial, invalid JSON, unverified sources, timeout, and Claude unavailability
must keep the Story blocked or in repair. Codex may take over only within the
same Story and unchanged authorization boundary.

## Two-Stage Adapter-Validated Mode (FR-ADP-001..010)

When the gateway/model combination returns `structured-output-empty` under
`--json-schema`, the research skill may select the explicit
`adapter-validated` profile. Development-system routes such runs as follows:

- The run must record `schemaEnforcementMode` and `providerNativeSchema`
  honestly. A silent downgrade from `provider-native` to `adapter-validated`
  is a P0 `silent-native-downgrade` and keeps the Story blocked.
- Adapter failure classes (`structured-output-empty`,
  `evidence-ledger-missing`, `evidence-hash-unstable`,
  `unsupported-fact-introduced`, `serialization-tool-access`,
  `adapter-validation-failed`, `format-attempt-exhaustion`) propagate to the
  next state exactly like the native failure classes. None may map a result to
  `completed`.
- Development-system accepts an adapter-validated result only after the local
  Schema and semantic gates pass with zero P0/P1 findings and Codex reviews the
  frozen evidence ledger.
- `DS-OPT-20260827-001` remains blocked until a real GLM 5.2 + Exa canary and a
  full Research packet pass with zero P0/P1 findings (FR-ADP-009). A
  development-only packet must not execute the live canary.
