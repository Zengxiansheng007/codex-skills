# Checkpoint Schema Reference

## Core rule

Checkpoint granularity is business-subchain level:

- CP0 governance and intake baseline
- CP1 login state
- CP2 project / space switch
- CP3 module entry navigation
- CP4 page / modal open
- CP5 form field recognition and fill
- CP6 submit and result verification

UI actions such as click, input, select, scroll, and wait live inside a checkpoint as `steps`, not as separate checkpoints.

## Required top-level fields

- `checkpoint_id`
- `schema_version`
- `stage`
- `name`
- `status`
- `risk_level`
- `source_baseline`
- `execution_context`
- `depends_on`
- `validate`
- `evidence`
- `governance`
- `promotion_gate`
- `staleness_policy`

## Conditional fields

- `cleanup_policy` is required for write checkpoints.
- `failure_attribution` is required for failed / degraded / blocked checkpoints.
- `steps` is recommended for all checkpoints and required for trace-rich stages.

## Downstream views

- `ui_test_packet`
- `handoff_packet`
- `artifact_refs`
- `rag_packet`

