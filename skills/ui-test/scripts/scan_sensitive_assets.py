#!/usr/bin/env python3
"""Scan text assets for persisted credential values without echoing matches."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


STRONG_PATTERNS = (
    ("openai-key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("bearer-value", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{12,}")),
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
)
SENSITIVE_FIELD = r"password|passwd|api[_-]?key|access[_-]?token|refresh[_-]?token|cookie|authorization"
ASSIGNMENTS = (
    re.compile(rf"(?i)[\"'](?:{SENSITIVE_FIELD})[\"']\s*:\s*[\"']([^\"']+)[\"']"),
    re.compile(rf"(?i)(?<![\"'])\b(?:{SENSITIVE_FIELD})\b\s*=\s*[\"']([^\"']+)[\"']"),
)
PLACEHOLDERS = {"", "redacted", "placeholder", "example", "synthetic", "test-only", "<redacted>", "${env}", "env"}
SKIP_SUFFIXES = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".zip", ".trace"}


def scan(root: str | Path) -> dict:
    base = Path(root).resolve()
    findings = []
    for path in sorted(base.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            kinds = [kind for kind, pattern in STRONG_PATTERNS if pattern.search(line)]
            for assignment in ASSIGNMENTS:
                for match in assignment.finditer(line):
                    value = match.group(1).strip().lower()
                    if value not in PLACEHOLDERS and not value.startswith(("${", "<", "env:", "os.environ", "getenv")):
                        kinds.append("credential-literal")
            for kind in sorted(set(kinds)):
                findings.append({
                    "file": path.relative_to(base).as_posix(), "line": line_number, "kind": kind,
                    "line_digest": "sha256:" + hashlib.sha256(line.encode("utf-8")).hexdigest(),
                })
    return {"schema_version": "ui-test.sensitive-scan.v1", "status": "failed" if findings else "clear", "finding_count": len(findings), "findings": findings, "raw_values_persisted": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    args = parser.parse_args()
    result = scan(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
