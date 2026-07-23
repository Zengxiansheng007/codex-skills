# Cache Schema

Cache root defaults to `.figma-cache/` under the current working directory unless `--cache` is provided.

```text
.figma-cache/
  <file_key>/
    meta.json
    raw.json
    index.sqlite
    images/
      <node_id>__scale-<scale>__version-<version>.png
```

## meta.json

```json
{
  "file_key": "98osRfwb0IYqiImqsgwdIz",
  "name": "Design file name",
  "version": "2365947538556608551",
  "last_modified": "2026-06-17T06:58:37Z",
  "synced_at": "2026-06-17T08:00:00Z",
  "total_nodes": 278858,
  "indexed_nodes": 221709
}
```

## SQLite Tables

`nodes`

- `file_key`
- `node_id`
- `parent_id`
- `page_name`
- `name`
- `type`
- `text`
- `node_json`

`nodes_fts`

- FTS5 virtual table over `name`, `page_name`, and `text`.

## Version Rules

- Cache is valid only when `meta.version == remote.version`.
- Image cache keys must include `version`.
- Search and image commands must reject stale cache before reading indexes or files.

