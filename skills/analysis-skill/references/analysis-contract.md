# Analysis Contract

## Inputs

- A local Skill directory or ZIP archive.
- Optional target profile: `codex`, `open-agent-skills`, `claude`, or `cursor`.
- Optional analysis purpose: `auto`, `adoption`, `redesign`, or `adoption-and-redesign`.
- An output HTML path outside the target artifact.

GitHub URLs must first be retrieved into a local, pinned, read-only snapshot by a separately approved source-retrieval step.

## R0 Output

`analyze_skill.py` creates an HTML report and a sibling JSON index.

Legacy-compatible fields:

- `artifact`: source path, hash, selected SKILL.md, file inventory, and staging notes;
- `frontmatter`: parsed YAML or parse error context;
- `capabilities`: scripts, URLs, and environment references;
- `findings`: rule ID, severity, file, line, message, remediation, and evidence IDs;
- `decision`: static status, recommendation, and R3 prerequisites.

Redesign-oriented fields:

- `analysisPurpose`: `adoption`, `redesign`, or `adoption-and-redesign`;
- `securityAnalysis`: compatibility wrapper around legacy security fields;
- `designAnalysis`: problem solved, target users, trigger scenarios, skill type, success criteria, strengths, gaps, headings, and confidence;
- `runtimeModel`: inputs, workflow stages, decision points, declared scripts, referenced guidance, outputs, and validation loop;
- `resourceRoleMatrix`: role, load phase, reference status, and orphan/scriptization candidates for resources;
- `logicDesign`: modules, pipeline, data model, decision rules, confidence rules, error handling, extension points, and resource-role summary;
- `redesignBacklog`: prioritized repair/refactor tasks with affected files, evidence IDs, and acceptance criteria;
- `evalRecommendations`: regression and eval ideas for security, design logic, runtime chain, malicious input, and migration compatibility;
- `evidenceIndex`: machine-readable evidence records used by findings and backlog items.

The static decision is intentionally conservative:

- invalid structure: `rerun`;
- P0 finding: `review-required`;
- scripts, URLs, or P1 finding: `sandbox-only`;
- otherwise: `review-required` because behavior is not yet verified.

## Evidence Rules

- Preserve hashes, rule IDs, paths, line numbers, tool version, timestamp, and evidence IDs.
- Escape target content before embedding it in HTML or JSON script blocks.
- Do not embed full file bodies, secrets, private URLs, credentials, or private identifiers in the report.
- An unavailable check must be reported as `unverified`, never passed implicitly.
- Every P0/P1 finding and redesign backlog item should reference `evidenceIds`.

## Compatibility Rules

- Existing consumers of `artifact`, `frontmatter`, `capabilities`, `findings`, `summary`, and `decision` must continue to work.
- New consumers should prefer `securityAnalysis` for security review and `designAnalysis` + `runtimeModel` + `logicDesign` for redesign preparation.
- If the analysis purpose is adoption-only, redesign fields may be brief but must remain valid JSON objects or arrays.
