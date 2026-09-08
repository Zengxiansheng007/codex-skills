# MetaGPT Module Admission

Read this before reusing MetaGPT code rather than its role, SOP or Artifact concepts.

Classify each candidate exactly once:

- `contract-reuse`: reuse the public design contract without importing code;
- `code-admission-candidate`: code reuse is requested and all gates pass;
- `reference-only`: evidence is incomplete or code is not admitted;
- `rejected`: the candidate changes Completion Authority or bypasses the unified contract.

Code admission requires license, pinned version, dependency list, isolation boundary, fail-closed exception policy, deterministic test evidence and rollback. The `governance bypass` check runs before missing evidence so it cannot be hidden by a weaker `reference-only` result.

Any admitted module remains behind an adapter and must preserve existing schemas, governed states and Codex completion authority. Use `evaluate_module_admission` and `schemas/module-admission.schema.json`.

Trace: FR-005, FR-032, AC-002, AC-032 through AC-034.
