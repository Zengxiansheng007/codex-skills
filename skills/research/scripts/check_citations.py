#!/usr/bin/env python3
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


def main():
    if len(sys.argv) != 2:
        print("usage: check_citations.py path/to/report.html", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    urls = re.findall(r'https?://[^"\'<>\s)]+', text)
    if not urls:
        raise AssertionError("no http(s) citation URLs found")
    bad = [u for u in urls if not urlparse(u).netloc]
    if bad:
        raise AssertionError(f"bad URLs: {bad[:5]}")
    print(f"ok: {len(urls)} URL(s) found in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
