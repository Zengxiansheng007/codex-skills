"""Secret scan and quarantine helpers that never echo matched values."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


PATTERNS = (
    re.compile(r"(?i)\b(password|passwd|token|cookie|authorization|storage[_-]?state|api[_-]?key|secret)\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{8,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
)


def scan_text(text: str) -> list[str]:
    return [f"pattern-{index + 1}" for index, pattern in enumerate(PATTERNS) if pattern.search(text)]


def scan_value(value: Any, path: str = "$") -> list[dict[str, str]]:
    if isinstance(value, dict):
        findings: list[dict[str, str]] = []
        for key, child in value.items():
            if scan_text(str(key)):
                findings.append({"path": f"{path}.{key}", "reason": "sensitive-key"})
            findings.extend(scan_value(child, f"{path}.{key}"))
        return findings
    if isinstance(value, list):
        findings: list[dict[str, str]] = []
        for index, child in enumerate(value):
            findings.extend(scan_value(child, f"{path}[{index}]"))
        return findings
    if isinstance(value, str) and scan_text(value):
        return [{"path": path, "reason": "sensitive-value"}]
    return []


def quarantine_record(source: str, findings: list[dict[str, str]], reason: str = "secret-detected") -> dict[str, Any]:
    return {
        "schema_version": "ui-test.quarantine.v1",
        "source_digest": "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "reason": reason,
        "finding_count": len(findings),
        "findings": [{"path": item["path"], "reason": item["reason"]} for item in findings],
        "raw_values_persisted": False,
    }


def scan_file(path: str | Path) -> dict[str, Any]:
    source = Path(path).read_text(encoding="utf-8")
    findings = scan_text(source)
    record = quarantine_record(str(path), [{"path": "$", "reason": item} for item in findings]) if findings else {
        "schema_version": "ui-test.secret-scan.v1", "source": str(path), "status": "clear", "raw_values_persisted": False
    }
    if findings:
        record["status"] = "quarantined"
    return record
