# Packet Mapping Rules

## ui-test-packet -> handoff_packet

- Keep source lineage.
- Carry over `failure_history`, `retry_history`, `required_fix_points`.
- Replace verbose narrative with compact continuation fields.
- Normalize the downstream action into `next_action`.

## ui-test-packet -> prompt_packet

- Extract the next Midscene request objective.
- Convert historical failure into revision notes.
- Keep constraints explicit and short.
- Add `expected_verification` that can be checked by Codex.

## ui-test-packet -> artifact_refs

- Keep only stable references.
- Prefer identifiers over prose.
- Preserve screenshot, trace, report, packet, and json references.

