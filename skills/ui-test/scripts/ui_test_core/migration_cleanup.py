"""Read-only inventory, controlled migration planning and zero-delete cleanup dry-runs."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from .case_contracts import canonical_hash, validate_document
from .path_utils import canonical_display_path, io_path


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def classify_asset(relative_path: str) -> str:
    parts = [part.lower() for part in Path(relative_path).parts]
    name = parts[-1] if parts else ""
    if any(part in {".idea", ".vscode"} for part in parts):
        return "ide"
    if any(part in {"__pycache__", ".pytest_cache", ".cache"} for part in parts) or name.endswith((".pyc", ".pyo")):
        return "cache"
    if "_private" in parts:
        return "private-ref"
    if "_tmp" in parts:
        return "tmp"
    if any("backup" in part for part in parts):
        return "backup"
    if "releases" in parts:
        return "historical-release"
    if "runs" in parts:
        return "historical-run"
    if "reports" in parts or name.endswith(".html"):
        return "historical-report"
    if ".codex" in parts:
        return "governance"
    return "current-formal"


def inventory_tree(root: str | Path, *, schema_version: str = "ui-test.cleanup-inventory.v2", generated_at: str | None = None) -> dict[str, Any]:
    display_base = canonical_display_path(root)
    base = io_path(display_base)
    files = []
    for path in sorted((item for item in base.rglob("*") if item.is_file()), key=lambda item: item.as_posix()):
        relative = path.relative_to(base).as_posix()
        files.append({"path": relative, "size": path.stat().st_size, "sha256": _file_hash(path), "asset_class": classify_asset(relative)})
    inventory = {
        "schema_version": schema_version,
        "root": str(display_base),
        "generated_at": generated_at or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "file_count": len(files),
        "files": files,
    }
    inventory["inventory_hash"] = canonical_hash(files)
    if validate_document(inventory, "asset-inventory-v2.schema.json"):
        raise ValueError("E_ASSET_INVENTORY_SCHEMA_INVALID")
    return inventory


def create_migration_plan(inventory: dict[str, Any], cases: Iterable[dict[str, str]]) -> dict[str, Any]:
    normalized = sorted((dict(item) for item in cases), key=lambda item: (item["case_id"], item["branch_id"]))
    plan = {
        "schema_version": "ui-test.migration-plan.v2",
        "source_inventory_hash": inventory["inventory_hash"],
        "cases": normalized,
        "historical_policy": "immutable-audit-only",
        "formal_apply_authorized": False,
    }
    plan["plan_hash"] = canonical_hash(plan)
    if validate_document(plan, "migration-plan-v2.schema.json"):
        raise ValueError("E_MIGRATION_PLAN_SCHEMA_INVALID")
    return plan


def create_cleanup_plan(inventory: dict[str, Any], *, referenced_paths: set[str] | None = None) -> dict[str, Any]:
    referenced_paths = referenced_paths or set()
    items = []
    for item in inventory["files"]:
        asset_class = item["asset_class"]
        if item["path"] in referenced_paths or asset_class in {"historical-release", "historical-run", "historical-report", "private-ref", "governance", "current-formal"}:
            disposition = "retain"
        elif asset_class in {"cache", "ide"}:
            disposition = "cleanup-eligible"
        elif asset_class in {"tmp", "backup"}:
            disposition = "hold"
        else:
            disposition = "unresolved"
        items.append({
            "path": item["path"],
            "sha256": item["sha256"],
            "asset_class": asset_class,
            "disposition": disposition,
            "reason": f"policy:{asset_class}",
        })
    plan = {
        "schema_version": "ui-test.cleanup-plan.v2",
        "source_inventory_hash": inventory["inventory_hash"],
        "items": items,
        "delete_authorized": False,
    }
    plan["plan_hash"] = canonical_hash(plan)
    if validate_document(plan, "cleanup-plan-v2.schema.json"):
        raise ValueError("E_CLEANUP_PLAN_SCHEMA_INVALID")
    return plan


def dry_run_cleanup(plan: dict[str, Any], before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    material = {key: value for key, value in plan.items() if key != "plan_hash"}
    if plan.get("plan_hash") != canonical_hash(material):
        raise ValueError("E_CLEANUP_PLAN_HASH_MISMATCH")
    if before["inventory_hash"] != plan["source_inventory_hash"]:
        raise ValueError("E_CLEANUP_INVENTORY_MISMATCH")
    result = {
        "schema_version": "ui-test.cleanup-result.v2",
        "plan_hash": plan["plan_hash"],
        "status": "dry-run",
        "deleted_count": 0,
        "before_inventory_hash": before["inventory_hash"],
        "after_inventory_hash": after["inventory_hash"],
        "unchanged": before["inventory_hash"] == after["inventory_hash"],
    }
    if validate_document(result, "cleanup-result-v2.schema.json"):
        raise ValueError("E_CLEANUP_RESULT_SCHEMA_INVALID")
    return result
