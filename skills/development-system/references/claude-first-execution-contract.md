# Claude-First Execution Contract

Read this before selecting the code executor.

## Mandatory Decision Gate

Multi-file changes, Skill development, complex repairs and cross-module work are Claude-first when the full preauthorization matches and Claude is available. Codex local execution must carry one recognized exception: documentation-only, single-file non-behavioral change or simple local task.

Claude is an executor. It receives one Story, its Anchor and exact workspace boundary; it returns structured feedback and evidence. Codex reviews every changed file and validation result.

Codex may take over the same Story only when Claude is unavailable, reaches the configured timeout or reaches the invalid-feedback threshold, and takeover remains inside the original policy. Preserve the Story ID, round counters, permissions and evidence lineage.

Trace: FR-018, FR-019, FR-024, FR-025, FR-026, AC-012, AC-013, AC-016.
