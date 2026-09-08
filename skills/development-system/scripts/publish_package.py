"""Fixed, dry-run-first publish planner for governed document packages.

This module deliberately separates planning from external GitHub/GitBook writes.
The live adapter must supply an exact approved target and return evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from document_manifest_runtime import register_or_reuse, validate_manifest


def preflight(manifest: dict[str, Any], content: str, approval: dict[str, Any]) -> dict[str, Any]:
    errors = validate_manifest(manifest, content)
    if approval.get("approved") is not True:
        errors.append("approval-required")
    if approval.get("targetRepository") != manifest.get("paths", {}).get("githubRepository"):
        errors.append("target-repository-mismatch")
    return {
        "status": "preflight-passed" if not errors else "failed",
        "errors": errors,
        "actions": ["git-preflight", "sensitive-scan", "manifest-validation", "approval-check"] if not errors else [],
        "externalWrite": False,
    }


def plan_publish(manifest: dict[str, Any], content: str, approval: dict[str, Any], registry: list[dict[str, Any]]) -> dict[str, Any]:
    check = preflight(manifest, content, approval)
    record = register_or_reuse(manifest, registry)
    if check["status"] != "preflight-passed":
        return {"status": "failed", "preflight": check, "idempotency": record, "next": "repair-or-review"}
    return {
        "status": "preflight-passed",
        "preflight": check,
        "idempotency": record,
        "next": "requires-explicit-live-adapter-and-target-binding",
        "github": "not-written",
        "gitbook": "not-written",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--content", required=True, type=Path)
    parser.add_argument("--approval", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    approval = json.loads(args.approval.read_text(encoding="utf-8"))
    result = plan_publish(manifest, args.content.read_text(encoding="utf-8"), approval, [])
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "preflight-passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
