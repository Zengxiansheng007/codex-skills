# Software Company Profile Pipeline Contract

Read this when activating the MetaGPT-inspired business workflow.

## Profiles And Artifacts

`product-requirement` owns the PRD and acceptance baseline. `architect` owns module, interface, data, risk and rollback design. `project-planner` owns Phase/Story decomposition and dependency order. `engineer` owns implementation and unit evidence. `qa` owns independent test evidence and defect classification. All are private `development-system.private` profiles; Codex remains the control plane.

Each profile consumes a versioned upstream Artifact Envelope and may run only after its entry gate passes. It produces a new envelope with stable ID/version, owner, source Anchor, mapped FR/AC, source references and change type. Engineer claims and QA evidence remain separate.

The pipeline is requirement -> architecture -> plan/story -> implementation -> QA -> Codex completion review. Defects route to the Artifact Owner and reopen only impacted downstream gates.

Trace: FR-004, FR-006 through FR-009, FR-012, FR-028, AC-004, AC-017 through AC-020.
