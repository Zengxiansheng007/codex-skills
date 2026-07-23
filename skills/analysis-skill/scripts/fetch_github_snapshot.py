#!/usr/bin/env python3
"""Fetch a public GitHub repository snapshot pinned to a commit SHA."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


MAX_ARCHIVE_BYTES = 75 * 1024 * 1024
GITHUB_RE = re.compile(r"^(?:https://github\.com/)?(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$")


def parse_repo(value: str) -> tuple[str, str]:
    match = GITHUB_RE.match(value.strip())
    if not match:
        raise ValueError("repo must be owner/repo or https://github.com/owner/repo")
    return match.group("owner"), match.group("repo")


def request_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "analysis-skill"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def download(url: str, destination: Path) -> str:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "analysis-skill"})
    digest = hashlib.sha256()
    total = 0
    with urllib.request.urlopen(request, timeout=90) as response, destination.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_ARCHIVE_BYTES:
                raise ValueError("downloaded archive exceeds 75MB safety limit")
            digest.update(chunk)
            handle.write(chunk)
    return digest.hexdigest()


def safe_extract(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as package:
        total = 0
        for entry in package.infolist():
            name = PurePosixPath(entry.filename)
            if name.is_absolute() or ".." in name.parts or "\x00" in entry.filename:
                raise ValueError(f"unsafe archive entry: {entry.filename}")
            total += entry.file_size
            if total > MAX_ARCHIVE_BYTES:
                raise ValueError("expanded archive exceeds 75MB safety limit")
        package.extractall(destination)


def write_html(metadata: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    embedded = json.dumps(metadata, ensure_ascii=False).replace("</", "<\\/")
    rows = "".join(
        f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>"
        for key, value in metadata.items()
        if key != "files"
    )
    output.write_text(
        f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>GitHub Skill 快照元数据</title>
<style>body{{font-family:Microsoft YaHei,Arial,sans-serif;background:#f6f8fb;color:#17202a}}main{{max-width:980px;margin:24px auto;background:#fff;border:1px solid #d8e0e7;padding:28px}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #d8e0e7;padding:8px;text-align:left;vertical-align:top}}th{{width:220px;background:#eef3f8}}code{{word-break:break-all}}</style></head>
<body><main><h1>GitHub Skill 只读快照</h1><p>该报告仅证明源码已按 commit 固定到本地快照，不代表 Skill 安全或可采用。</p><table>{rows}</table></main>
<script type="application/json" id="github-snapshot-metadata">{embedded}</script></body></html>""",
        encoding="utf-8",
    )


def fetch(repo: str, ref: str, output_dir: Path) -> dict[str, Any]:
    owner, name = parse_repo(repo)
    commit_url = f"https://api.github.com/repos/{owner}/{name}/commits/{ref}"
    commit = request_json(commit_url)
    sha = commit["sha"]
    snapshot_dir = output_dir / f"github-{owner}-{name}-{sha[:12]}"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="analysis-github-") as temp:
        archive = Path(temp) / "snapshot.zip"
        archive_hash = download(f"https://api.github.com/repos/{owner}/{name}/zipball/{sha}", archive)
        safe_extract(archive, snapshot_dir)
    files = sorted(str(path.relative_to(snapshot_dir)).replace("\\", "/") for path in snapshot_dir.rglob("*") if path.is_file())
    return {
        "tool": "analysis-skill.github-snapshot",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "repo": f"{owner}/{name}",
        "requestedRef": ref,
        "commitSha": sha,
        "commitUrl": commit_url,
        "snapshotDir": str(snapshot_dir),
        "archiveSha256": archive_hash,
        "fileCount": len(files),
        "files": files[:500],
        "truncatedFileList": len(files) > 500,
        "networkBoundary": "public GitHub API only; no credentials used",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch public GitHub source as a pinned local snapshot")
    parser.add_argument("repo", help="owner/repo or https://github.com/owner/repo")
    parser.add_argument("--ref", required=True, help="branch, tag, or commit SHA to pin")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True, help="HTML report path")
    parser.add_argument("--allow-network", action="store_true", help="required explicit network gate")
    args = parser.parse_args(argv)
    if not args.allow_network:
        print("network access is disabled; pass --allow-network after approval", file=sys.stderr)
        return 2
    try:
        metadata = fetch(args.repo, args.ref, args.output_dir)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        write_html(metadata, args.report)
        print(f"snapshot: {metadata['snapshotDir']}")
        print(f"report: {args.report}")
        return 0
    except Exception as error:
        print(f"github snapshot failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
