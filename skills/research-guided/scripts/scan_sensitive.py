#!/usr/bin/env python3
"""Scan a skill folder for sensitive patterns."""
import re, sys, json
from pathlib import Path
SECRET_RE = re.compile(r"sk-[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._-]+|(?i:password|token|cookie)\s*[:=]\s*\S+")
def scan(root):
    root = Path(root); findings = []
    for p in root.rglob("*"):
        if not p.is_file() or "__pycache__" in p.parts: continue
        if p.suffix.lower() in {".pyc",".png",".jpg",".jpeg",".gif",".ico"}: continue
        rel = p.relative_to(root).as_posix()
        try: text = p.read_text(encoding="utf-8", errors="replace")
        except: continue
        for i, ln in enumerate(text.splitlines(), 1):
            if "SECRET_RE" in ln: continue
            if SECRET_RE.search(ln):
                findings.append({"file":rel,"line":i,"pattern":"secret","text":ln[:100]})
    status = "fail" if findings else "pass"
    return {"status": status, "findings": findings}
if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    result = scan(root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(1 if result["status"] == "fail" else 0)
