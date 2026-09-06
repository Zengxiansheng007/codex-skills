# Grill Requirements Adapter

The canonical Grill-to-PRD adapter is maintained by `write-prd` at `../../write-prd/references/grill-system-requirements-adapter.md`. Read it before every clarification round; do not fork its V2 return contract.

The receiving PRD writer must treat `phase`, `result`, `closureEvidence`, `writebackPolicy`, `protectedAssets`, `processArtifacts`, `exceptions`, `recovery`, `checkpoints`, and `writebackReceipts` as the handoff evidence. A report, question confirmation, return from a callee, or legacy result is not write authority.
