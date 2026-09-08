"""Deterministic post-implementation review for requirement artifacts.

The tool creates candidate revisions only. It never edits the baseline anchor or
promotes a candidate to an approved/RC state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


SENSITIVE_PATTERNS = (
    re.compile(r"(?:ghp_|github_pat_|sk-[A-Za-z0-9_-]{12,})"),
    re.compile(r"(?i)(?:password|secret|api[_-]?key|access[_-]?token|cookie)\s*[:=]\s*[^\s,]+"),
)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sensitive_paths(value: Any, path: str = chr(36)) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            found.extend(sensitive_paths(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(sensitive_paths(item, f"{path}[{index}]"))
    elif isinstance(value, str):
        if any(pattern.search(value) for pattern in SENSITIVE_PATTERNS):
            found.append(path)
    return found


def validate_manifest(manifest: Any, label: str) -> list[str]:
    if not isinstance(manifest, dict):
        return [f"{label}:root-not-object"]
    if not isinstance(manifest.get("artifacts"), list):
        return [f"{label}:artifacts-not-array"]
    errors: list[str] = []
    for index, artifact in enumerate(manifest["artifacts"]):
        if not isinstance(artifact, dict):
            errors.append(f"{label}:artifact-{index}-not-object")
            continue
        for field in ("artifactId", "version", "contentHash"):
            if not str(artifact.get(field, "")).strip():
                errors.append(f"{label}:artifact-{index}-missing-{field}")
    return errors


def _index(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["artifactId"]): item for item in items}


def review(baseline: Any, observed: Any) -> dict[str, Any]:
    baseline_errors = validate_manifest(baseline, "baseline")
    observed_errors = validate_manifest(observed, "observed")
    sensitive = sensitive_paths(baseline) + sensitive_paths(observed)
    if baseline_errors or observed_errors or sensitive:
        reasons = baseline_errors + observed_errors
        if sensitive:
            reasons.append("sensitive-input")
        return {
            "status": "blocked",
            "classification": "invalid-or-sensitive-input",
            "reasons": reasons,
            "sensitivePaths": sensitive,
            "candidateRevisions": [],
            "retestRequired": False,
        }

    base = _index(baseline["artifacts"])
    actual = _index(observed["artifacts"])
    changed: list[dict[str, Any]] = []
    missing: list[str] = []
    for artifact_id, expected in sorted(base.items()):
        current = actual.get(artifact_id)
        if current is None:
            missing.append(artifact_id)
            continue
        if current.get("contentHash") != expected.get("contentHash"):
            changed.append({
                "artifactId": artifact_id,
                "baselineHash": expected.get("contentHash"),
                "observedHash": current.get("contentHash"),
                "reason": current.get("changeReason", "observed implementation evidence differs"),
            })

    implementation = observed.get("implementation", {})
    evidence = observed.get("evidence", [])
    semantic_change = bool(implementation.get("semanticRequirementChange"))
    has_evidence = isinstance(evidence, list) and len(evidence) > 0
    candidate_revisions = [
        {
            "artifactId": item["artifactId"],
            "revisionType": "candidate-revision",
            "supersedes": item["artifactId"],
            "reason": item["reason"],
            "approvalStatus": "need-review",
        }
        for item in changed
    ]

    if semantic_change:
        classification = "requirements-review"
        status = "blocked"
        reasons = ["semantic-requirement-change-requires-new-anchor"]
    elif changed or missing:
        classification = "implementation-drift"
        status = "blocked" if not has_evidence else "candidate-revision-needed"
        reasons = ["observed-artifact-diff"]
        if missing:
            reasons.append("baseline-artifact-missing-from-observation")
    elif not has_evidence:
        classification = "insufficient-evidence"
        status = "blocked"
        reasons = ["implementation-evidence-required"]
    else:
        classification = "no-drift"
        status = "reviewed"
        reasons = []

    return {
        "status": status,
        "classification": classification,
        "reasons": reasons,
        "changedArtifacts": changed,
        "missingArtifacts": missing,
        "candidateRevisions": candidate_revisions,
        "retestRequired": bool(changed or semantic_change),
        "approvalStatus": "not-approved",
        "rcStatus": "not-generated",
    }


def build_report(baseline: Any, observed: Any) -> dict[str, Any]:
    result = review(baseline, observed)
    return {
        "reportType": "landed-review",
        "reportVersion": "1.0.0",
        "baselineAnchorId": baseline.get("anchorId") if isinstance(baseline, dict) else None,
        "baselineInputHash": sha256(baseline),
        "observedInputHash": sha256(observed),
        "baselineImmutable": True,
        "generatedBy": "development-system/landed-review",
        "result": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--observed", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        baseline = load_json(args.baseline)
        observed = load_json(args.observed)
        report = build_report(baseline, observed)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"landed-review failed: {exc}")
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["result"]["status"] != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
