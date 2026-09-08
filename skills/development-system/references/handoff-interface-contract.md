# Independent Handoff Interface Contract

Read this before calling `handoff-system` or another independent execution Skill.

## Boundary

`development-system` owns routing, Requirement Anchor, permissions, state transitions and final completion. `handoff-system` owns packet transport and execution feedback. Neither Skill copies or silently replaces the other.

Every declared interface must provide `skillName`, `version`, `owner`, `inputSchemaRef`, `outputSchemaRef`, `allowedActions`, `forbiddenActions`, `evidenceContract` and `statusMapping`. Validate it with `validate_skill_interface` and `schemas/skill-interface.schema.json`.

## Exchange

1. Codex creates a versioned Anchor and Story.
2. Codex builds a complete-field handoff packet mapped to FR/AC.
3. A dry-run proves packet, workspace, command and output paths.
4. Live execution is allowed only when every preauthorization dimension matches.
5. The adapter returns feedback, manifest and evidence references.
6. Codex validates schema, drift, unmapped actions and risk before selecting one governed state.

Invalid or unmapped feedback is `repair-needed`; repeated same-root invalid feedback opens the circuit. An Agent completion claim is never completion evidence by itself.

## Feedback Validation Evidence

`CompletionEvaluator` requires the actual `feedback` object plus `feedbackValidation` evidence. The evidence must carry non-empty `schemaRef` and `validatorId`, a 64-character lowercase SHA-256 `feedbackHash` equal to the canonical hash of the supplied feedback object, `ok=true`, `errorCount=0`, `errors=[]` or absent, and non-empty `validatedAt`. A bare `feedbackValid` boolean alone can no longer satisfy completion. This Skill does not duplicate the handoff-system feedback schema; the evidence object proves an external owner validated the actual packet.

Trace: FR-003, FR-010, FR-011, FR-013, AC-006, AC-009, AC-014, AC-021, AC-034, REPAIR-ST-001.
