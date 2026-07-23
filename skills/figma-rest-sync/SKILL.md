---
name: figma-rest-sync
description: Read, validate, cache, search, and export Figma design data through the Figma REST API for Claude Code workflows. Use when Claude Code needs the latest Figma UI prototype data, frame lookup, design text search, comments/notes retrieval, frame image export, or a local searchable index from Figma design files. This skill requires a Figma Personal Access Token on first use and must stop if the online Figma version cannot be verified or differs from the local cache.
---

# Figma REST Sync

Use this skill to work with Figma files through the REST API while preserving strict version consistency. The online Figma file is the source of truth. Local cache only accelerates queries after the online version is verified.

## Hard Rules

- Require `FIGMA_TOKEN` before any Figma API call. If missing, ask the user for a Figma Personal Access Token and stop.
- Before any cache-backed query, image export, or brief generation, call online version check first.
- Stop if the online Figma file cannot be reached, token is invalid, access is denied, file is missing, or request times out.
- Stop if local `meta.version` differs from remote `version`.
- Do not use stale cache as fallback.
- Do not print tokens, write tokens into outputs, or place tokens in skill files.

## Workflow

1. Parse the Figma URL into `file_key` and optional `node_id`.
2. Run `scripts/figma_sync.py check --file <figma-url-or-file-key>` to validate token and read remote version.
3. If no local cache exists, run `scripts/figma_sync.py sync --file <figma-url-or-file-key>` after user confirms first sync.
4. For lookup, run `scripts/figma_sync.py search --file <figma-url-or-file-key> --query "<keywords>"`.
5. For a selected frame, run `scripts/figma_sync.py frame --file <figma-url>`.
6. For image export, run `scripts/figma_sync.py image --file <figma-url> --scale 0.5`.
7. For Claude-ready output, run `scripts/figma_sync.py brief --file <figma-url>`.

All query commands enforce online version validation before reading local cache.

## References

- Read `references/error_policy.md` when handling token, network, permission, cache, or version failures.
- Read `references/cache_schema.md` when implementing or reviewing cache/index changes.
- Read `references/test_matrix.md` before validating this skill or adding new Figma commands.

## Output Expectations

Return concise Markdown for Claude Code:

- file name and `file_key`
- remote version and local version
- selected `node_id`
- matched frame/page name
- relevant text snippets or comments
- local image path when exported
- clear blocking error and user recovery step when validation fails

