"""Publish the approved A/B announcement assets through the governed compiler."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path

from ui_test_core.case_contracts import canonical_hash, lower_to_case_ir, validate_document, validate_source_case
from ui_test_core.compiler import build_dependency_graph, compile_case
from ui_test_core.product_aggregate import render_product_aggregate
from ui_test_core.semantic_rules import validate_p0_suite, validate_semantics


FORMAL_ROOT = Path(r"D:\UI-Test\tianjin__天津项目组\ops-platform__运营管理平台\bops-ops-platform__运营管理平台")
PRODUCT_ROOT = FORMAL_ROOT.parent
CASE_ROOT = FORMAL_ROOT / "operations-config__运营配置" / "message-management__消息管理" / "announcement-management__公告管理" / "create__创建"
REGISTRY_PATH = CASE_ROOT / "_shared" / "dependency-registry.json"
PROJECT_CONFIG_PATH = CASE_ROOT / "_shared" / "config" / "ui-test.project.yaml"


def _repair_legacy_text(value):
    if isinstance(value, dict):
        return {key: _repair_legacy_text(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_repair_legacy_text(item) for item in value]
    if isinstance(value, str):
        current = value
        for _ in range(3):
            try:
                repaired = current.encode("gb18030").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                break
            if repaired == current:
                break
            current = repaired
        return current
    return value


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _legacy_text(value) -> bool:
    text = json.dumps(value, ensure_ascii=False)
    return any(token in text for token in ("锛", "鑿", "鐧", "杩", "鍒", "澶", "绠", "绱", "鏉", "鎻", "瀵", "璇", "搴"))


def _case_paths(case_id: str, branch_id: str) -> dict[str, Path]:
    branch = CASE_ROOT / "cases" / case_id / "branches" / branch_id
    return {
        "source": branch / "source" / "source-case.json",
        "manifest": branch / "manifest.json",
        "human": branch / "views" / "human.md",
        "midscene": branch / "views" / "midscene.json",
        "resolved": branch / "resolved" / "resolved-case.json",
        "playwright": branch / "playwright-test.py",
        "receipt": branch / "compile-receipt.json",
    }


def _relative(path: Path) -> Path:
    return path.relative_to(Path(r"D:\UI-Test"))


def main(*, dry_run: bool = False) -> int:
    cases = [
        ("BOPS-ANNOUNCEMENT-P0-A", "system-announcement"),
        ("BOPS-ANNOUNCEMENT-P0-B", "popup-announcement"),
    ]
    case_paths = {case_id: _case_paths(case_id, branch_id) for case_id, branch_id in cases}
    product_files = [
        PRODUCT_ROOT / "运维管理系统.总测试用例.md",
        PRODUCT_ROOT / "运维管理系统.总测试用例.outline.json",
        PRODUCT_ROOT / "运维管理系统.总测试用例.manifest.json",
    ]
    legacy_product_files = [
        PRODUCT_ROOT / "运营管理平台.总测试用例.md",
        PRODUCT_ROOT / "运营管理平台.总测试用例.outline.json",
        PRODUCT_ROOT / "运营管理平台.总测试用例.manifest.json",
    ]
    superseded_root = Path(r"D:\UI-Test\_tmp\superseded-product-aggregate-20260825-v1.1-r3")
    backup_root = Path(r"D:\UI-Test\_tmp\formal-publish-backup-20260825-total-human-view-v1.1-r3")
    stage_root = Path(r"D:\UI-Test\_tmp\formal-publish-stage-20260825-total-human-view-v1.1-r3")
    if backup_root.exists() and not (backup_root / "backup-manifest.json").exists():
        shutil.rmtree(backup_root)
    if stage_root.exists() and not (stage_root / "stage-marker.json").exists():
        shutil.rmtree(stage_root)
    if backup_root.exists() or stage_root.exists() or superseded_root.exists():
        raise RuntimeError("publish staging or backup already exists; refusing to overwrite")

    existing_files = [REGISTRY_PATH, PROJECT_CONFIG_PATH]
    for paths in case_paths.values():
        existing_files.extend(paths.values())
    existing_files.extend(path for path in product_files + legacy_product_files if path.is_file())
    backup_root.mkdir(parents=True, exist_ok=False)
    backup_manifest = {"schema_version": "ui-test.publish-backup.v1", "created_at": datetime.now().astimezone().isoformat(), "files": []}
    for index, path in enumerate(existing_files, 1):
        if not path.is_file():
            continue
        target = backup_root / f"{index:04d}__{path.name}"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        backup_manifest["files"].append({"path": str(_relative(path)), "backup_path": str(target.relative_to(backup_root)), "sha256": _sha256(path)})
    _write_json(backup_root / "backup-manifest.json", backup_manifest)

    registry = _json(REGISTRY_PATH)
    graph_cases = []
    source_cases = []
    for case_id, branch_id in cases:
        paths = case_paths[case_id]
        source = _repair_legacy_text(_json(paths["source"]))
        source["display_name"] = {
            "BOPS-ANNOUNCEMENT-P0-A": "创建系统公告核心冒烟",
            "BOPS-ANNOUNCEMENT-P0-B": "创建首页弹窗公告核心冒烟",
        }[case_id]
        source["precondition_group"] = "announcement-create-common"
        source["special_preconditions"] = []
        if case_id.endswith("-A"):
            source["steps"]["assertions"][0]["expected_result"] = "成功提示或列表存在本次公告"
        if _legacy_text(source):
            raise RuntimeError(f"legacy encoding remains in {case_id}")
        structural = validate_source_case(source)
        semantic = validate_semantics(source, source_path=str(paths["source"]))
        if structural or any(issue.get("blocking") for issue in semantic):
            raise RuntimeError(json.dumps({"case_id": case_id, "structural": structural, "semantic": semantic}, ensure_ascii=False))
        refs = [item["id"] for item in source["precondition_flow_refs"] + source["page_object_refs"] + source["component_refs"]]
        case_ir = lower_to_case_ir(source, source_path=str(paths["source"]))
        refs += case_ir["binding_refs"]
        graph_cases.append({"case_id": case_id, "dependency_refs": sorted(set(refs))})
        source_cases.append((case_id, branch_id, source, case_ir))

    suite_issues = validate_p0_suite([item[3] for item in source_cases])
    if any(issue.get("blocking") for issue in suite_issues):
        raise RuntimeError(json.dumps(suite_issues, ensure_ascii=False))
    graph = build_dependency_graph(registry, graph_cases)
    compiled = []
    for case_id, branch_id, source, case_ir in source_cases:
        result = compile_case(case_ir, graph, compiler_version="1.0.0", renderer_version="1.0.0", schema_version="1", config_fingerprint=canonical_hash(registry))
        if validate_document(result["manifest"], "case-manifest.schema.json") or validate_document(result["compile_receipt"], "compile-receipt.schema.json"):
            raise RuntimeError(f"generated contract invalid: {case_id}")
        result["source_case"] = source
        compiled.append((case_id, branch_id, result))

    aggregate = render_product_aggregate(
        [{"case_ir": result["case_ir"], "manifest": result["manifest"]} for _, _, result in compiled],
        display_registry={
            "project_groups": {"tianjin": "天津项目组"},
            "products": {"ops-platform": "运维管理系统"},
            "systems": {"bops-ops-platform": "运维管理系统"},
            "modules": {"operations-config": "运营配置", "message-management": "消息管理", "announcement-management": "公告管理"},
            "functions": {"create": "创建"},
        },
        config_fingerprint=canonical_hash(registry),
    )
    if validate_document(aggregate["outline"], "product-outline.schema.json") or validate_document(aggregate["manifest"], "product-aggregate-manifest.schema.json"):
        raise RuntimeError("product aggregate contract invalid")
    for name, content in aggregate["outputs"].items():
        if isinstance(content, str) and _legacy_text(content):
            raise RuntimeError(f"legacy encoding remains in aggregate {name}")

    stage_root.mkdir(parents=True, exist_ok=False)
    _write_json(stage_root / "stage-marker.json", {"schema_version": "ui-test.publish-stage.v1"})
    staged_targets: dict[Path, Path] = {}
    for case_id, branch_id, result in compiled:
        paths = case_paths[case_id]
        outputs = {
            paths["source"]: result["source_case"],
            paths["manifest"]: result["manifest"],
            paths["human"]: result["outputs"]["human.md"],
            paths["midscene"]: result["outputs"]["midscene.json"],
            paths["resolved"]: result["resolved_ir"],
            paths["playwright"]: result["outputs"]["playwright-test.py"],
            paths["receipt"]: result["compile_receipt"],
        }
        for target, content in outputs.items():
            staged = stage_root / f"{len(staged_targets) + 1:04d}__{target.name}"
            if isinstance(content, str):
                staged.parent.mkdir(parents=True, exist_ok=True)
                staged.write_text(content, encoding="utf-8", newline="\n")
            else:
                _write_json(staged, content)
            staged_targets[target] = staged
    aggregate_manifest = aggregate["manifest"]
    aggregate_outputs = {
        product_files[0]: aggregate["outputs"]["运维管理系统.总测试用例.md"],
        product_files[1]: aggregate["outputs"]["运维管理系统.总测试用例.outline.json"],
        product_files[2]: aggregate_manifest,
    }
    if dry_run:
        print(json.dumps({
            "status": "dry-run",
            "targets": [str(path) for paths in case_paths.values() for path in paths.values()] + [str(path) for path in product_files] + [str(PROJECT_CONFIG_PATH)],
            "legacy_superseded": [str(path) for path in legacy_product_files if path.is_file()],
            "source_hashes": {case_id: result["manifest"]["source_hash"] for case_id, _, result in compiled},
            "aggregate": aggregate_manifest,
        }, ensure_ascii=False, indent=2))
        return 0
    for target, content in aggregate_outputs.items():
        staged = stage_root / f"{len(staged_targets) + 1:04d}__{target.name}"
        if isinstance(content, str):
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_text(content, encoding="utf-8", newline="\n")
        else:
            _write_json(staged, content)
        staged_targets[target] = staged

    config_text = PROJECT_CONFIG_PATH.read_text(encoding="utf-8")
    if config_text.count("product_name: 运营管理平台") != 1 or config_text.count("display_name: 运营管理平台") != 1:
        raise RuntimeError("unexpected project config display-name baseline")
    config_text = config_text.replace("product_name: 运营管理平台", "product_name: 运维管理系统")
    config_text = config_text.replace("display_name: 运营管理平台", "display_name: 运维管理系统")
    config_stage = stage_root / f"{len(staged_targets) + 1:04d}__{PROJECT_CONFIG_PATH.name}"
    config_stage.parent.mkdir(parents=True, exist_ok=True)
    config_stage.write_text(config_text, encoding="utf-8", newline="\n")
    staged_targets[PROJECT_CONFIG_PATH] = config_stage

    for target, staged in staged_targets.items():
        if target.suffix in {".json"}:
            json.loads(staged.read_text(encoding="utf-8"))
        if _sha256(staged).startswith("sha256:") is False:
            raise RuntimeError(f"staged hash failed: {staged}")
    for target, staged in staged_targets.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        staged.replace(target)
    superseded_root.mkdir(parents=True, exist_ok=False)
    superseded = []
    for legacy in legacy_product_files:
        if legacy.is_file():
            target = superseded_root / legacy.name
            shutil.move(str(legacy), str(target))
            superseded.append({"old_path": str(_relative(legacy)), "new_path": str(target.relative_to(Path(r"D:\UI-Test")))})
    _write_json(superseded_root / "superseded-manifest.json", {
        "schema_version": "ui-test.superseded-aggregate.v1",
        "reason": "display-name-and-renderer-resync",
        "replacement_root": str(_relative(PRODUCT_ROOT)),
        "files": superseded,
    })
    shutil.rmtree(stage_root)

    post = {"backup": str(backup_root), "superseded": str(superseded_root), "published_files": [], "source_hashes": {}, "aggregate": aggregate_manifest}
    for target in staged_targets:
        post["published_files"].append(str(target))
    for case_id, branch_id, result in compiled:
        post["source_hashes"][case_id] = result["manifest"]["source_hash"]
    _write_json(backup_root / "publish-result.json", post)
    print(json.dumps(post, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    raise SystemExit(main(dry_run=parser.parse_args().dry_run))
