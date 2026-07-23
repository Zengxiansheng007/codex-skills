#!/usr/bin/env python3
import argparse
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen


API_BASE = "https://api.figma.com/v1"


class FigmaError(Exception):
    def __init__(self, code, message, next_action, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.next_action = next_action
        self.details = details or {}

    def to_dict(self):
        return {
            "ok": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "next_action": self.next_action,
                "details": self.details,
            },
        }


def parse_figma_url(value):
    match = re.search(r"figma\.com/(?:file|design)/([^/?#]+)", value)
    if not match:
        return value, None
    file_key = match.group(1)
    query = parse_qs(urlparse(value).query)
    node_id = query.get("node-id", [None])[0]
    if node_id:
        node_id = unquote(node_id).replace("-", ":")
    return file_key, node_id


def require_token():
    token = os.environ.get("FIGMA_TOKEN", "").strip()
    if not token:
        raise FigmaError(
            "FIGMA_TOKEN_MISSING",
            "Figma Personal Access Token is required.",
            "Ask the user to provide a Figma Personal Access Token and set it as FIGMA_TOKEN before continuing.",
        )
    return token


def request_json(path, token, timeout=120):
    req = Request(
        f"{API_BASE}{path}",
        headers={"X-Figma-Token": token, "User-Agent": "claude-code-figma-rest-sync"},
    )
    try:
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 401:
            raise FigmaError("FIGMA_TOKEN_INVALID", "Figma rejected the token.", "Generate a new token with access to this file.")
        if exc.code == 403:
            raise FigmaError("FIGMA_FILE_FORBIDDEN", "Token does not have access to this file.", "Grant file access or use a token from an authorized account.")
        if exc.code == 404:
            raise FigmaError("FIGMA_FILE_NOT_FOUND", "Figma file or node was not found.", "Check the Figma URL, file key, and node id.")
        raise FigmaError("FIGMA_VERSION_CHECK_FAILED", f"Figma API returned HTTP {exc.code}.", "Retry after checking Figma API status and permissions.")
    except URLError as exc:
        raise FigmaError("FIGMA_NETWORK_UNAVAILABLE", str(exc.reason), "Restore network access and rerun the version check.")
    except TimeoutError:
        raise FigmaError("FIGMA_NETWORK_UNAVAILABLE", "Figma request timed out.", "Retry when the network is stable.")
    except json.JSONDecodeError:
        raise FigmaError("FIGMA_VERSION_CHECK_FAILED", "Figma response was not valid JSON.", "Retry the request and verify the API response.")


def remote_meta(file_key, token):
    data = request_json(f"/files/{file_key}?depth=1", token)
    version = data.get("version")
    last_modified = data.get("lastModified")
    if not version or not last_modified:
        raise FigmaError(
            "FIGMA_VERSION_CHECK_FAILED",
            "Remote version or lastModified was missing.",
            "Retry the version check; do not continue with local cache.",
        )
    return {
        "file_key": file_key,
        "name": data.get("name", ""),
        "version": version,
        "last_modified": last_modified,
        "page_count": len(data.get("document", {}).get("children", []) or []),
    }


def cache_paths(cache_root, file_key):
    root = Path(cache_root) / file_key
    return {
        "root": root,
        "meta": root / "meta.json",
        "raw": root / "raw.json",
        "db": root / "index.sqlite",
        "images": root / "images",
    }


def read_json(path, error_code):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FigmaError("FIGMA_CACHE_MISSING", f"Cache file is missing: {path}", "Run sync after online version check passes.")
    except json.JSONDecodeError:
        raise FigmaError(error_code, f"Cache file is corrupt: {path}", "Delete the corrupt cache and run sync again.")


def validate_cache(paths, remote):
    local = read_json(paths["meta"], "FIGMA_CACHE_CORRUPTED")
    local_version = local.get("version")
    if local_version != remote["version"]:
        raise FigmaError(
            "FIGMA_VERSION_MISMATCH",
            "Local Figma cache version differs from the online version.",
            "Run sync to refresh the cache, then retry after version check passes.",
            {"local_version": local_version, "remote_version": remote["version"], "file_key": remote["file_key"]},
        )
    return local


def flatten(node, page_name=None, parent_id=None):
    node_type = node.get("type")
    current_page = node.get("name") if node_type == "CANVAS" else page_name
    yield {
        "node_id": node.get("id", ""),
        "name": node.get("name", ""),
        "type": node_type or "",
        "page_name": current_page or "",
        "parent_id": parent_id or "",
        "text": node.get("characters", "") if node_type == "TEXT" else "",
        "node_json": json.dumps(
            {
                "id": node.get("id"),
                "name": node.get("name"),
                "type": node.get("type"),
                "absoluteBoundingBox": node.get("absoluteBoundingBox"),
                "layoutMode": node.get("layoutMode"),
                "children": [child.get("id") for child in node.get("children", []) or [] if child.get("id")],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
    }
    for child in node.get("children", []) or []:
        yield from flatten(child, current_page, node.get("id"))


def create_index(db_path, rows):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as db:
        db.executescript(
            """
            DROP TABLE IF EXISTS nodes;
            DROP TABLE IF EXISTS nodes_fts;
            CREATE TABLE nodes (
              file_key TEXT NOT NULL,
              node_id TEXT PRIMARY KEY,
              parent_id TEXT,
              page_name TEXT,
              name TEXT,
              type TEXT,
              text TEXT,
              node_json TEXT
            );
            CREATE VIRTUAL TABLE nodes_fts USING fts5(node_id UNINDEXED, name, page_name, text);
            """
        )
        db.executemany(
            "INSERT INTO nodes(file_key,node_id,parent_id,page_name,name,type,text,node_json) VALUES(?,?,?,?,?,?,?,?)",
            rows,
        )
        db.executemany(
            "INSERT INTO nodes_fts(node_id,name,page_name,text) VALUES(?,?,?,?)",
            [(row[1], row[4], row[3], row[6]) for row in rows],
        )


def cmd_check(args):
    token = require_token()
    file_key, _ = parse_figma_url(args.file)
    remote = remote_meta(file_key, token)
    print_json({"ok": True, "remote": remote})


def cmd_sync(args):
    token = require_token()
    file_key, _ = parse_figma_url(args.file)
    remote = remote_meta(file_key, token)
    paths = cache_paths(args.cache, file_key)
    started = time.perf_counter()
    data = request_json(f"/files/{file_key}", token, timeout=args.timeout)
    paths["root"].mkdir(parents=True, exist_ok=True)
    paths["raw"].write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    rows = []
    for item in flatten(data["document"]):
        if not item["node_id"]:
            continue
        rows.append((file_key, item["node_id"], item["parent_id"], item["page_name"], item["name"], item["type"], item["text"], item["node_json"]))
    create_index(paths["db"], rows)
    meta = {
        "file_key": file_key,
        "name": data.get("name") or remote["name"],
        "version": data.get("version") or remote["version"],
        "last_modified": data.get("lastModified") or remote["last_modified"],
        "synced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_nodes": len(rows),
        "indexed_nodes": len(rows),
    }
    paths["meta"].write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print_json({"ok": True, "meta": meta, "elapsed_seconds": round(time.perf_counter() - started, 3)})


def ensure_valid_cache(args):
    token = require_token()
    file_key, node_id = parse_figma_url(args.file)
    paths = cache_paths(args.cache, file_key)
    remote = remote_meta(file_key, token)
    local = validate_cache(paths, remote)
    if not paths["db"].exists():
        raise FigmaError("FIGMA_CACHE_MISSING", f"SQLite index is missing: {paths['db']}", "Run sync after online version check passes.")
    return file_key, node_id, paths, remote, local


def search_db(db_path, query, limit):
    terms = [part for part in re.split(r"\s+", query.strip()) if part]
    if not terms:
        return []
    like_terms = [f"%{term}%" for term in terms]
    sql = """
      SELECT node_id, name, type, page_name, text,
             ((CASE WHEN name LIKE ? THEN 4 ELSE 0 END) +
              (CASE WHEN page_name LIKE ? THEN 2 ELSE 0 END) +
              (CASE WHEN text LIKE ? THEN 1 ELSE 0 END)) AS score
      FROM nodes
      WHERE name LIKE ? OR page_name LIKE ? OR text LIKE ?
      ORDER BY score DESC, CASE type WHEN 'FRAME' THEN 0 WHEN 'CANVAS' THEN 1 WHEN 'TEXT' THEN 2 ELSE 3 END, name
      LIMIT ?
    """
    rows = []
    with sqlite3.connect(db_path) as db:
        for term in like_terms:
            rows.extend(db.execute(sql, [term, term, term, term, term, term, limit]).fetchall())
    seen = {}
    for row in rows:
        node_id = row[0]
        if node_id not in seen or row[5] > seen[node_id][5]:
            seen[node_id] = row
    return sorted(seen.values(), key=lambda row: (-row[5], 0 if row[2] == "FRAME" else 1, row[1]))[:limit]


def cmd_search(args):
    _, _, paths, remote, local = ensure_valid_cache(args)
    started = time.perf_counter()
    rows = search_db(paths["db"], args.query, args.limit)
    print_json(
        {
            "ok": True,
            "remote_version": remote["version"],
            "local_version": local["version"],
            "elapsed_seconds": round(time.perf_counter() - started, 4),
            "matches": [
                {"node_id": r[0], "name": r[1], "type": r[2], "page_name": r[3], "text_preview": (r[4] or "")[:240]}
                for r in rows
            ],
        }
    )


def cmd_frame(args):
    _, node_id, paths, remote, local = ensure_valid_cache(args)
    if not node_id:
        raise FigmaError("FIGMA_FILE_NOT_FOUND", "Figma URL does not contain node-id.", "Provide a Figma selection or frame URL with node-id.")
    with sqlite3.connect(paths["db"]) as db:
        row = db.execute("SELECT node_id,name,type,page_name,text,node_json FROM nodes WHERE node_id=?", [node_id]).fetchone()
    if not row:
        raise FigmaError("FIGMA_FILE_NOT_FOUND", f"Node not found in cache: {node_id}", "Run sync for the latest file and retry.")
    print_json(
        {
            "ok": True,
            "remote_version": remote["version"],
            "local_version": local["version"],
            "frame": {"node_id": row[0], "name": row[1], "type": row[2], "page_name": row[3], "text_preview": (row[4] or "")[:500], "node": json.loads(row[5])},
        }
    )


def cmd_image(args):
    token = require_token()
    file_key, node_id, paths, remote, local = ensure_valid_cache(args)
    if not node_id:
        raise FigmaError("FIGMA_FILE_NOT_FOUND", "Figma URL does not contain node-id.", "Provide a Figma selection or frame URL with node-id.")
    safe_node = node_id.replace(":", "-").replace(";", "_")
    scale = str(args.scale).replace(".", "_")
    out = paths["images"] / f"{safe_node}__scale-{scale}__version-{remote['version']}.png"
    if out.exists() and out.stat().st_size > 0:
        print_json({"ok": True, "cached": True, "image_path": str(out), "node_id": node_id, "version": remote["version"]})
        return
    image_meta = request_json(f"/images/{file_key}?ids={node_id.replace(':', '%3A')}&format=png&scale={args.scale}", token)
    image_url = image_meta.get("images", {}).get(node_id)
    if not image_url:
        raise FigmaError("FIGMA_FILE_NOT_FOUND", f"Figma did not return an image URL for node {node_id}.", "Check node id and whether the node is exportable.")
    req = Request(image_url, headers={"User-Agent": "claude-code-figma-rest-sync"})
    paths["images"].mkdir(parents=True, exist_ok=True)
    try:
        with urlopen(req, timeout=args.timeout) as response:
            out.write_bytes(response.read())
    except Exception as exc:
        raise FigmaError("FIGMA_NETWORK_UNAVAILABLE", f"Failed to download Figma image: {exc}", "Retry image export when the network is stable.")
    print_json({"ok": True, "cached": False, "image_path": str(out), "node_id": node_id, "version": remote["version"]})


def cmd_brief(args):
    _, node_id, paths, remote, local = ensure_valid_cache(args)
    if node_id:
        with sqlite3.connect(paths["db"]) as db:
            row = db.execute("SELECT node_id,name,type,page_name,text FROM nodes WHERE node_id=?", [node_id]).fetchone()
        matches = [row] if row else []
    else:
        matches = search_db(paths["db"], args.query, args.limit)
    lines = [
        f"# Figma Brief",
        "",
        f"- file_key: `{remote['file_key']}`",
        f"- file: {local.get('name') or remote.get('name')}",
        f"- version: `{remote['version']}`",
        f"- last_modified: `{remote['last_modified']}`",
        "",
        "## Matches",
    ]
    for row in matches:
        if not row:
            continue
        lines.extend([f"- `{row[0]}` | {row[2]} | {row[3]} | {row[1]}", f"  - text: {(row[4] or '')[:240]}"])
    print("\n".join(lines))


def print_json(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Strict Figma REST sync for Claude Code skills.")
    parser.add_argument("--cache", default=".figma-cache")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check")
    p.add_argument("--file", required=True)
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("sync")
    p.add_argument("--file", required=True)
    p.add_argument("--timeout", type=int, default=600)
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("search")
    p.add_argument("--file", required=True)
    p.add_argument("--query", required=True)
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("frame")
    p.add_argument("--file", required=True)
    p.set_defaults(func=cmd_frame)

    p = sub.add_parser("image")
    p.add_argument("--file", required=True)
    p.add_argument("--scale", type=float, default=0.5)
    p.add_argument("--timeout", type=int, default=300)
    p.set_defaults(func=cmd_image)

    p = sub.add_parser("brief")
    p.add_argument("--file", required=True)
    p.add_argument("--query", default="")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=cmd_brief)

    args = parser.parse_args()
    try:
        args.func(args)
    except FigmaError as exc:
        print_json(exc.to_dict())
        sys.exit(2)


if __name__ == "__main__":
    main()
