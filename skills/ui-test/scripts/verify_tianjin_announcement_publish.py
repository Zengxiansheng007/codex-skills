from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ui_test_core.case_contracts import canonical_hash, validate_document


FORMAL_ROOT = Path(r"D:\UI-Test\tianjin__天津项目组\ops-platform__运营管理平台\bops-ops-platform__运营管理平台")
PRODUCT_ROOT = FORMAL_ROOT.parent
CASE_ROOT = FORMAL_ROOT / "operations-config__运营配置" / "message-management__消息管理" / "announcement-management__公告管理" / "create__创建"


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    results = {"status": "passed", "cases": {}, "product": {}}
    for case_id, branch_id, content_variant in [
        ("BOPS-ANNOUNCEMENT-P0-A", "system-announcement", "普通文本输入框"),
        ("BOPS-ANNOUNCEMENT-P0-B", "popup-announcement", "富文本编辑器"),
    ]:
        branch = CASE_ROOT / "cases" / case_id / "branches" / branch_id
        source = load(branch / "source" / "source-case.json")
        manifest = load(branch / "manifest.json")
        human = (branch / "views" / "human.md").read_text(encoding="utf-8")
        midscene = load(branch / "views" / "midscene.json")
        resolved = load(branch / "resolved" / "resolved-case.json")
        receipt = load(branch / "compile-receipt.json")
        if source["case_id"] != case_id or source["branch_id"] != branch_id:
            raise AssertionError(f"scope mismatch: {case_id}")
        content_step = next(step for step in source["steps"]["feature"] if step["step_id"] == "F03")
        if content_step["parameters"][0]["display_value"] != content_variant:
            raise AssertionError(f"content variant mismatch: {case_id}")
        if case_id.endswith("-A") and "弹窗公告版本为最新" in json.dumps(source, ensure_ascii=False):
            raise AssertionError("A still contains popup-version assertion")
        if case_id.endswith("-A") and "弹窗公告版本为最新" in human:
            raise AssertionError("A Human View still contains popup-version assertion")
        if "| 序号 | 操作 | 参数/数据 | 预期结果 |" not in human:
            raise AssertionError(f"Human View table contract missing: {case_id}")
        if manifest["status"] != "in_sync" or manifest["source_hash"] != receipt["source_hash"]:
            raise AssertionError(f"manifest/receipt mismatch: {case_id}")
        for name, expected in manifest["artifacts"].items():
            path = {"human.md": branch / "views" / "human.md", "midscene.json": branch / "views" / "midscene.json", "playwright-test.py": branch / "playwright-test.py"}[name]
            actual = canonical_hash(path.read_text(encoding="utf-8")) if path.suffix in {".md", ".py"} else canonical_hash(load(path))
            if actual != expected:
                raise AssertionError(f"artifact hash mismatch: {case_id}/{name}")
        if midscene["metadata"]["source_hash"] != manifest["source_hash"] or resolved["source_hash"] != manifest["source_hash"]:
            raise AssertionError(f"lineage mismatch: {case_id}")
        results["cases"][case_id] = {"source_hash": manifest["source_hash"], "content_variant": content_variant, "status": manifest["status"]}

    aggregate_manifest_path = PRODUCT_ROOT / "运维管理系统.总测试用例.manifest.json"
    aggregate_manifest = load(aggregate_manifest_path)
    aggregate_outline = load(PRODUCT_ROOT / "运维管理系统.总测试用例.outline.json")
    aggregate_markdown = (PRODUCT_ROOT / "运维管理系统.总测试用例.md").read_text(encoding="utf-8")
    if validate_document(aggregate_manifest, "product-aggregate-manifest.schema.json"):
        raise AssertionError("aggregate manifest schema invalid")
    if validate_document(aggregate_outline, "product-outline.schema.json"):
        raise AssertionError("aggregate outline schema invalid")
    if aggregate_manifest["status"] != "in_sync" or aggregate_manifest["is_unmodified"] is not True:
        raise AssertionError("aggregate state invalid")
    if set(item["case_id"] for item in aggregate_manifest["included_cases"]) != {"BOPS-ANNOUNCEMENT-P0-A", "BOPS-ANNOUNCEMENT-P0-B"}:
        raise AssertionError("aggregate case set invalid")
    if "运维管理系统" not in aggregate_markdown or "参数/数据" not in aggregate_markdown:
        raise AssertionError("aggregate markdown content invalid")
    results["product"] = {"root": str(PRODUCT_ROOT), "status": aggregate_manifest["status"], "included_cases": aggregate_manifest["included_cases"]}
    print(json.dumps(results, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
