#!/usr/bin/env python3
import sys
from pathlib import Path

from research_process_loop import extract_block, validate_process_loop


def strict_required(metadata):
    return bool(metadata.get("strictLoopRequired") or metadata.get("highImpact") or metadata.get("impactLevel") in {"high", "critical"})


def main():
    if len(sys.argv) != 2:
        print("usage: validate_research_process_loop.py path/to/report.html", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    metadata = extract_block(text, "research-metadata")
    result = validate_process_loop(text, required=strict_required(metadata))
    if result["enabled"]:
        print(f"ok: {path} ({result['findings']} findings, {result['followups']} follow-ups, {result['closures']} closures)")
    else:
        print(f"ok: {path} (strict closure not required)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
