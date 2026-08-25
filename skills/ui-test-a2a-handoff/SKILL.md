---
name: ui-test-a2a-handoff
description: Convert ui-test-packet into a stable A2A-compatible handoff_packet, prompt_packet, and artifact_refs bundle for Codex to keep refining Midscene requests. Use when the user asks for a UI-test交接协议层, prompt转换层, packet to packet mapping, failure_history preservation, retry_history preservation, or artifact reference hygiene. Do not use for real A2A transport, browser execution, or checkpoint runtime.
---

# UI-Test A2A Handoff

## Purpose

This skill only does one thing: transform a source `ui-test-packet` into a deterministic, reviewable, and replayable handoff bundle for the next Codex turn.

It preserves:
- `failure_history`
- `retry_history`
- `required_fix_points`
- `artifact_refs`
- `next_action`

It does **not**:
- run browser automation
- send remote A2A messages
- manage checkpoint runtime
- rewrite large prompt prose into the packet
- mutate business pages or credentials

## Inputs

- `ui-test-packet` JSON
- previous handoff packet if present
- optional Codex review notes
- stable evidence references only

## Outputs

- `handoff_packet`
- `prompt_packet`
- `artifact_refs`

## Operating rules

1. Preserve source lineage with `source_packet_id` and, when derived, `parent_packet_id`.
2. Never drop historical failures or retries when a new revision is created.
3. Do not embed long prompt prose in `artifact_refs`.
4. Keep outputs deterministic for the same normalized input.
5. If a field is unsafe, malformed, or ambiguous, reject it. Do not downgrade missing `steps`, non-read-only safety, empty `forbidden_actions`, or sensitive `artifact_refs`.
6. Treat `handoff_packet` as the contract for Codex continuation, not as a transport protocol.

## Workflow

1. Validate the source packet shape.
2. Extract stable context and prior failures.
3. Build the minimal handoff contract.
4. Build the prompt packet with clear action, constraints, and expected verification.
5. Emit stable artifact references only; reject references containing credentials, cookies, tokens, passwords, `Bearer` values, or long prompt prose.
6. Produce a machine-readable summary for downstream review.

## References

- [Schema](references/schema.md)
- [Mapping](references/mapping.md)
- [Boundaries](references/boundaries.md)
- [Deterministic mapper](scripts/a2a_handoff.py)

## Validation

Run the bundled unit tests and confirm valid input maps deterministically while missing IDs and sensitive artifact references fail closed.

## Safety

Do not execute transport, browsers, external messages, or business writes. Reject credentials, authentication state, private raw URLs, and unreviewed prompt payloads.
