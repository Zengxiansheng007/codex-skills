# Research Routing Release 2026-09-08

Release marker: research-routing-20260908

The Research workflow is now split into three Skills:

- [research](../../skills/research/SKILL.md): common router; AnySearch is the default.
- [research-guided](../../skills/research-guided/SKILL.md): preserved research execution workflow; Claude first, with explicit user-selected Codex.
- [anysearch](../../skills/anysearch/SKILL.md): pinned official upstream capability package.

The development-system and handoff-feedback-reviewer references are updated to distinguish routing from the preserved guided execution profile.

## Routing and recovery

Unspecified provider selects AnySearch. Explicit Claude or Codex selects research-guided with that executor. The topic merely mentioning a provider does not select it.

A preconfigured ANYSEARCH_API_KEY environment value is required for AnySearch. Anonymous access and automatic registration are disabled in the governed router path. Recognized quota exhaustion can route to guided/Claude; every non-quota fault pauses immediately, with zero automatic retries.

A paused task cannot skip retrieval or complete from old evidence. Only an actual user resume directive permits recovery, and a successful recovery probe is required before completion or reinforcement.

## Verification

- Router offline behavior suite: 32 passed.
- Preserved guided repair and adapter regressions: 26 and 32 passed, plus Skill tests.
- Four changed-package structure and change-record validators: zero P0/P1/P2 findings.
- Global installation: five packages and 327 manifest files verified; nine installed checks passed.
- AnySearch live smoke: domain discovery, public search and content extraction succeeded without retry.
- Claude Code live canary: one actual Exa search on official Agent Skills documentation. One tool-free format repair corrected the resultCode field, without new retrieval. Original feedback schema, semantic checks and host handoff/quality gates passed.
- The configured Claude Code model connection was bailian/glm-5.2; this does not claim an Anthropic model was selected.

The original guided scripts and schemas remain byte-identical to the pre-split baseline. Global installation kept a recoverable local backup.

## Source and integrity

Official AnySearch v3.1.1 is pinned to commit 15b7ea5039983c9dee328be8c7c609f3eb86058e. LICENSE and NOTICE are retained. The GitHub-only .github workflow is excluded from the runtime payload.

[Public release manifest](release-manifest.json) lists the exact source file hashes. No credentials, raw invocation packets or private execution logs are published.

## Remaining boundaries

Real quota exhaustion was not forced on the account. The compatibility mapping remains conservative and pauses on unknown responses. Host semantic review remains necessary; code-level state checks are not an OS sandbox or a proof of source truth.

User environment updates do not retroactively change already running processes. The host must provide the configured environment to the CLI without putting credential values in command arguments.
