# Error Policy

Figma REST data must be strongly version-validated. Any command that depends on local cache must first confirm that the online Figma file is reachable and that the local cache version equals the remote version.

## Blocking Errors

Use these stable codes:

- `FIGMA_TOKEN_MISSING`: `FIGMA_TOKEN` is not set.
- `FIGMA_TOKEN_INVALID`: Figma rejects the token with 401.
- `FIGMA_FILE_FORBIDDEN`: token lacks access, usually 403.
- `FIGMA_FILE_NOT_FOUND`: file key or node id is invalid, usually 404.
- `FIGMA_NETWORK_UNAVAILABLE`: DNS, connection, TLS, or socket failure.
- `FIGMA_VERSION_CHECK_FAILED`: online version cannot be read or parsed.
- `FIGMA_VERSION_MISMATCH`: local and remote versions differ.
- `FIGMA_CACHE_MISSING`: local cache does not exist.
- `FIGMA_CACHE_CORRUPTED`: meta, index, or raw cache cannot be parsed.

## Required Behavior

- Print the error code, reason, and next action.
- Do not continue to search, export, or summarize after a blocking error.
- Do not silently use stale local cache.
- Do not print the token.

## Recovery Messages

- Missing token: ask user to provide a Figma Personal Access Token and set it as `FIGMA_TOKEN`.
- Invalid token: ask user to generate a new token and ensure it can access the file.
- Version mismatch: ask user to run `sync` to refresh the local cache, then retry.
- Cache missing: ask user to run first sync after token and file access are verified.
- Network unavailable: ask user to restore network access and rerun version check.

