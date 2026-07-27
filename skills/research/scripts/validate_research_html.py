#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

from research_process_loop import validate_process_loop

REQUIRED_BLOCKS = ["research-metadata", "evidence-index", "search-log", "run-status"]


def extract_block(text, block_id):
    pattern = re.compile(
        rf"<script\s+type=[\"']application/json[\"']\s+id=[\"']{re.escape(block_id)}[\"']\s*>(.*?)</script>",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise AssertionError(f"missing JSON block: {block_id}")
    return match.group(1).strip()


def strict_required(metadata):
    return bool(metadata.get("strictLoopRequired") or metadata.get("highImpact") or metadata.get("impactLevel") in {"high", "critical"})


def main():
    if len(sys.argv) != 2:
        print("usage: validate_research_html.py path/to/report.html", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    if "<!doctype html>" not in text.lower():
        raise AssertionError("missing <!doctype html>")
    if "<main" not in text.lower() or "</main>" not in text.lower():
        raise AssertionError("missing main content")
    parsed = {}
    for block_id in REQUIRED_BLOCKS:
        parsed[block_id] = json.loads(extract_block(text, block_id))
    status = parsed["run-status"].get("status")
    if status not in {"complete", "partial", "blocked"}:
        raise AssertionError("run-status.status must be complete, partial, or blocked")
    validate_process_loop(text, required=strict_required(parsed["research-metadata"]))
    print(f"ok: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
