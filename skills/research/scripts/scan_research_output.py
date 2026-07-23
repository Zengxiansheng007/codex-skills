#!/usr/bin/env python3
import re
import sys
from pathlib import Path

PATTERNS = {
    "openai_or_gateway_key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9._-]+", re.IGNORECASE),
    "password_assignment": re.compile(r"password\s*[:=]\s*\S+", re.IGNORECASE),
    "cookie_assignment": re.compile(r"cookie\s*[:=]\s*\S+", re.IGNORECASE),
    "token_assignment": re.compile(r"token\s*[:=]\s*\S+", re.IGNORECASE),
}


def main():
    if len(sys.argv) != 2:
        print("usage: scan_research_output.py path/to/report.html", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    findings = []
    for name, pattern in PATTERNS.items():
        if pattern.search(text):
            findings.append(name)
    if findings:
        raise AssertionError(f"potential sensitive data found: {', '.join(findings)}")
    print(f"ok: no obvious secrets in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
