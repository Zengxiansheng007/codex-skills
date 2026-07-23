#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def extract(text, block_id):
    pattern = re.compile(
        rf'<script\s+type=["\']application/json["\']\s+id=["\']{re.escape(block_id)}["\']\s*>(.*?)</script>',
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise AssertionError(f"missing {block_id}")
    return json.loads(match.group(1).strip())


def main():
    if len(sys.argv) != 2:
        print("usage: validate_embedded_evidence.py path/to/report.html", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    index = extract(text, "evidence-index")
    claims = index.get("claims", [])
    sources = {s.get("id") for s in index.get("sources", [])}
    if not claims:
        raise AssertionError("evidence-index.claims must not be empty")
    for claim in claims:
        status = claim.get("status")
        if status not in {"supported", "weak", "conflicted", "unsupported"}:
            raise AssertionError(f"invalid claim status: {status}")
        evidence_ids = claim.get("evidenceIds", [])
        if status != "unsupported" and not evidence_ids:
            raise AssertionError(f"claim {claim.get('id')} has no evidence")
        missing = [e for e in evidence_ids if e not in sources]
        if missing:
            raise AssertionError(f"claim {claim.get('id')} references missing sources: {missing}")
    print(f"ok: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
