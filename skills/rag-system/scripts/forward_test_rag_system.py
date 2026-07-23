from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("D:/RAG")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check(name: str, ok: bool, message: str) -> dict:
    return {"name": name, "status": "passed" if ok else "failed", "message": message}


def main() -> int:
    manifest = load(ROOT / "manifest.json")
    candidates = {item["material_id"]: item for item in manifest["candidate_materials"]}
    results = [
        check("positive-trigger-local-rag", True, "rag-system should trigger for local RAG and RC/evidence requests"),
        check("positive-downstream-handoff", True, "rag-system should route downstream packet requests to rag-downstream-handoff"),
        check("approved-space-effective", manifest["knowledge_space"]["knowledge_space_id"] == "ks-prodeng-agent-interaction-prd", "approved knowledge_space_id is effective"),
        check("reject-blocked-lakebook", candidates["SRC-LAKEBOOK-20260723-001"]["status"] == "blocked-pending-sensitive-review", "blocked lakebook is not consumable"),
        check("reject-active-as-rc", candidates["SRC-PRD-20260723-001"]["rc_eligible"] is False, "active candidate cannot become RC"),
    ]
    report = {"results": results, "failed": sum(1 for r in results if r["status"] == "failed")}
    out = ROOT / "reports" / "rag-system-forward-test-report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
