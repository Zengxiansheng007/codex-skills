#!/usr/bin/env python3
"""Run only the accepted-result -> scholar ingest boundary.

This entry does not initialize state, advance phases, or perform retrieval.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from phase_bridge import build_event
from scholar_result_adapter import build_payload


EXPECTED_BASELINE_COMMIT = "e7ce1cbe657f2e0386f075f9aa9f6ead7171876e"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest an accepted Research result into the fixed scholar baseline")
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--baseline-root", required=True, type=Path)
    parser.add_argument("--story-id", required=True)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        result = _load(args.result)
        expected_ledger_sha256 = _load(args.ledger).get("ledgerSha256")
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=args.baseline_root,
            capture_output=True, text=True, encoding="utf-8", check=True,
        ).stdout.strip()
        if commit != EXPECTED_BASELINE_COMMIT:
            raise ValueError(f"baseline commit mismatch: {commit}")
        data = build_payload(result, expected_ledger_sha256=expected_ledger_sha256)
        event = build_event(result, story_id=args.story_id, baseline_commit=commit)
        if data["status"] != "ready":
            output = {"status": "blocked", "adapter": data, "event": event}
            code = 4
        else:
            ingests: list[dict[str, Any]] = []
            with tempfile.TemporaryDirectory(prefix="scholar-ingest-") as tmp:
                script = args.baseline_root / "scripts" / "research_state.py"
                for index, payload in enumerate(data["payloads"]):
                    payload_path = Path(tmp) / f"payload-{index}.json"
                    payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                    completed = subprocess.run(
                        [sys.executable, str(script), "--state", str(args.state), "ingest", "--input", str(payload_path)],
                        cwd=args.baseline_root, capture_output=True, text=True,
                        encoding="utf-8", errors="replace",
                    )
                    if completed.returncode != 0:
                        raise RuntimeError(completed.stdout or completed.stderr or "baseline ingest failed")
                    ingests.append(json.loads(completed.stdout))
            output = {"status": "ingested", "adapter": data, "event": event, "ingests": ingests}
            code = 0
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError, RuntimeError) as exc:
        output = {"status": "blocked", "failureClass": "baseline-entry-failed", "error": str(exc)}
        code = 5

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
