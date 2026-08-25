# Schema Contract

## Source packet (minimum)

- `packet_id` - unique source packet id
- `schema_version` - source schema version
- `objective` - what the next agent should continue
- `scope` - in-scope and out-of-scope boundary
- `safety` - forbidden actions and read-only constraints
- `steps` - prior step list if any
- `artifact_refs` - stable evidence refs
- `failure_history` - accumulated failures and reasons
- `retry_history` - prior prompt attempts and revisions
- `required_fix_points` - next-round mandatory corrections
- `next_action` - one of the approved actions

## handoff_packet (minimum)

- `handoff_id`
- `source_packet_id`
- `parent_packet_id` (required for derived packets)
- `handoff_stage`
- `decision_status`
- `failure_history`
- `retry_history`
- `required_fix_points`
- `artifact_refs`
- `next_action`

## prompt_packet (minimum)

- `prompt_id`
- `source_packet_id`
- `objective`
- `prompt_goal`
- `constraints`
- `allowed_actions`
- `forbidden_actions`
- `expected_verification`
- `revision_notes`

## artifact_refs

Stable references only:
- file path
- packet id
- report id
- screenshot path
- trace path
- json path

Do not store long natural-language blocks here.
Do not store credentials, cookies, tokens, passwords, authorization headers, or bearer-style values here.
