# Test Matrix

## Positive Cases

- Valid `FIGMA_TOKEN` and accessible Figma file returns remote version with `check`.
- First `sync` creates `meta.json`, `raw.json`, and `index.sqlite`.
- `search` for `任务中心-分支合并任务` returns frame `705:13742` for the known test file.
- `image` for node `705:13742` exports a PNG and reuses cache on repeated calls.
- `brief` returns Markdown with file, version, node, page, matched text, and image path when available.

## Blocking Cases

- Missing `FIGMA_TOKEN` returns `FIGMA_TOKEN_MISSING` and stops.
- Invalid token returns `FIGMA_TOKEN_INVALID` and stops.
- Forbidden file returns `FIGMA_FILE_FORBIDDEN` and stops.
- Missing file returns `FIGMA_FILE_NOT_FOUND` and stops.
- Network failure returns `FIGMA_NETWORK_UNAVAILABLE` or `FIGMA_VERSION_CHECK_FAILED` and stops.
- Missing cache returns `FIGMA_CACHE_MISSING` and stops.
- Local version mismatch returns `FIGMA_VERSION_MISMATCH` and stops.
- Corrupt meta or index returns `FIGMA_CACHE_CORRUPTED` and stops.

## Non-Regression Cases

- Token is never printed.
- `raw.json` is never returned to Claude Code as context.
- Cache-backed commands always run online version check first.
- Stale cache is never used as fallback.

