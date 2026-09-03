"""Product-level daily JSONL failure/repair source with recoverable projections."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from .case_contracts import canonical_hash, validate_document
from .file_lock import exclusive_file_lock
from .path_utils import io_path
from .strict_json import loads_strict, load_strict_json


# 中国标准时间当前采用固定 UTC+08:00，避免把未声明的 tzdata 包变成运行依赖。
CHINA_ZONE = timezone(timedelta(hours=8), name="Asia/Shanghai")
OPEN_EVENT_TYPES = {"failure-detected", "sync-required"}
CLOSE_EVENT_TYPES = {"repair-completed", "sync-completed"}
REPAIR_EVIDENCE = {
    "parameter-drift": {"parameter-hash", "sync-result", "release-verification"},
    "compile-sync": {"sync-result", "release-verification"},
    "release-integrity": {"release-verification"},
    "execution-guard": {"guard-test"},
    "test-failure": {"test-result"},
    "migration": {"migration-result", "release-verification"},
    "cleanup": {"cleanup-result"},
    "governance": {"validation-result"},
}


class FailureRepairStoreError(RuntimeError):
    """日志存储错误只输出稳定分类。"""


def problem_fingerprint(*, product_id: str, case_id: str, branch_id: str, category: str, source_files: Iterable[str] = ()) -> str:
    return canonical_hash({
        "product_id": product_id,
        "case_id": case_id,
        "branch_id": branch_id,
        "category": category,
        "source_files": sorted(set(source_files)),
    })


def make_event(
    *,
    event_type: str,
    idempotency_key: str,
    product_id: str,
    case_id: str,
    branch_id: str,
    category: str,
    summary: str,
    source_files: list[str] | None = None,
    evidence: list[dict[str, str]] | None = None,
    occurred_at: datetime | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    instant = (occurred_at or datetime.now(CHINA_ZONE)).astimezone(CHINA_ZONE)
    files = sorted(set(source_files or []))
    return {
        "schema_version": "ui-test.failure-repair-event.v2",
        "event_id": event_id or f"evt-{uuid.uuid4().hex}",
        "event_type": event_type,
        "idempotency_key": idempotency_key,
        "occurred_at": instant.isoformat(),
        "log_date": instant.date().isoformat(),
        "product_id": product_id,
        "case_id": case_id,
        "branch_id": branch_id,
        "problem_fingerprint": problem_fingerprint(product_id=product_id, case_id=case_id, branch_id=branch_id, category=category, source_files=files),
        "category": category,
        "summary": summary,
        "source_files": files,
        "evidence": evidence or [],
    }


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _atomic_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    payload = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not path.exists():
        return events
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise FailureRepairStoreError("E_HISTORY_JSONL_TRUNCATED")
    for line_number, raw_line in enumerate(raw.splitlines(), 1):
        if not raw_line.strip():
            raise FailureRepairStoreError(f"E_HISTORY_JSONL_EMPTY_LINE:{line_number}")
        try:
            event = loads_strict(raw_line.decode("utf-8", errors="strict"))
        except (UnicodeError, ValueError) as exc:
            raise FailureRepairStoreError(f"E_HISTORY_JSONL_INVALID:{line_number}") from exc
        if validate_document(event, "failure-repair-event.schema.json"):
            raise FailureRepairStoreError(f"E_HISTORY_EVENT_SCHEMA:{line_number}")
        events.append(event)
    return events


class FailureRepairEventStore:
    """Append events and atomically maintain index and unfinished projections."""

    def __init__(self, diagnostics_root: str | Path, *, product_id: str) -> None:
        self.root = io_path(diagnostics_root)
        self.product_id = product_id
        self.history_root = self.root / "failure-repair-history"
        self.index_path = self.history_root / "index.json"
        self.unfinished_path = self.root / "unfinished-repairs.json"
        self.intent_path = self.root / ".transactions" / "pending-event.json"
        self.lock_path = self.root / ".locks" / "failure-repair.lock"

    def _all_events(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        if not self.history_root.exists():
            return events
        for path in sorted(self.history_root.glob("????-??-??.jsonl")):
            events.extend(_read_jsonl(path))
        ids = [item["event_id"] for item in events]
        keys = [item["idempotency_key"] for item in events]
        if len(ids) != len(set(ids)) or len(keys) != len(set(keys)):
            raise FailureRepairStoreError("E_HISTORY_EVENT_DUPLICATE")
        return events

    def _validate_existing_projections(self, events: list[dict[str, Any]]) -> None:
        if self.index_path.exists():
            index = load_strict_json(self.index_path)
            if validate_document(index, "failure-history-index.schema.json"):
                raise FailureRepairStoreError("E_HISTORY_INDEX_INVALID")
            if index["event_count"] != len(events) or index["idempotency_keys"] != sorted(item["idempotency_key"] for item in events):
                raise FailureRepairStoreError("E_HISTORY_INDEX_MISMATCH")
        elif events:
            raise FailureRepairStoreError("E_HISTORY_INDEX_MISSING")
        if self.unfinished_path.exists():
            unfinished = load_strict_json(self.unfinished_path)
            if validate_document(unfinished, "unfinished-repairs.schema.json"):
                raise FailureRepairStoreError("E_UNFINISHED_PROJECTION_INVALID")
        elif events:
            raise FailureRepairStoreError("E_UNFINISHED_PROJECTION_MISSING")

    def _project(self, events: list[dict[str, Any]], generated_at: str) -> tuple[dict[str, Any], dict[str, Any]]:
        open_items: dict[str, dict[str, Any]] = {}
        for event in events:
            fingerprint = event["problem_fingerprint"]
            if event["event_type"] in OPEN_EVENT_TYPES:
                open_items[fingerprint] = {
                    "problem_fingerprint": fingerprint,
                    "category": event["category"],
                    "case_id": event["case_id"],
                    "branch_id": event["branch_id"],
                    "summary": event["summary"],
                    "source_files": event.get("source_files", []),
                    "opened_event_id": event["event_id"],
                    "updated_at": event["occurred_at"],
                }
            elif event["event_type"] in CLOSE_EVENT_TYPES:
                open_items.pop(fingerprint, None)
        days = []
        if self.history_root.exists():
            for path in sorted(self.history_root.glob("????-??-??.jsonl")):
                data = path.read_bytes()
                days.append({"date": path.stem, "file": path.name, "line_count": len(data.splitlines()), "sha256": _sha256_bytes(data)})
        index = {
            "schema_version": "ui-test.failure-history-index.v2",
            "product_id": self.product_id,
            "generated_at": generated_at,
            "days": days,
            "event_count": len(events),
            "idempotency_keys": sorted(item["idempotency_key"] for item in events),
        }
        index["projection_hash"] = canonical_hash(index)
        unfinished = {
            "schema_version": "ui-test.unfinished-repairs.v2",
            "product_id": self.product_id,
            "generated_at": generated_at,
            "items": sorted(open_items.values(), key=lambda item: (item["case_id"], item["branch_id"], item["problem_fingerprint"])),
        }
        unfinished["projection_hash"] = canonical_hash(unfinished)
        return index, unfinished

    def _check_repair_gate(self, event: dict[str, Any], events: list[dict[str, Any]]) -> None:
        if event["event_type"] not in CLOSE_EVENT_TYPES:
            return
        opened = next((item for item in reversed(events) if item["problem_fingerprint"] == event["problem_fingerprint"] and item["event_type"] in OPEN_EVENT_TYPES), None)
        if opened is None:
            raise FailureRepairStoreError("E_REPAIR_OPEN_PROBLEM_NOT_FOUND")
        required = REPAIR_EVIDENCE[event["category"]]
        supplied = {item["type"] for item in event["evidence"]}
        if not required.issubset(supplied):
            raise FailureRepairStoreError("E_REPAIR_EVIDENCE_INCOMPLETE")

    def append(self, event: dict[str, Any], *, fail_after: str | None = None) -> dict[str, Any]:
        if validate_document(event, "failure-repair-event.schema.json"):
            raise FailureRepairStoreError("E_HISTORY_EVENT_SCHEMA")
        if event["product_id"] != self.product_id:
            raise FailureRepairStoreError("E_HISTORY_PRODUCT_MISMATCH")
        with exclusive_file_lock(self.lock_path):
            pending = load_strict_json(self.intent_path) if self.intent_path.exists() else None
            if pending and pending.get("idempotency_key") != event["idempotency_key"]:
                raise FailureRepairStoreError("E_HISTORY_PENDING_TRANSACTION_CONFLICT")
            events = self._all_events()
            existing = next((item for item in events if item["idempotency_key"] == event["idempotency_key"]), None)
            if existing is not None:
                if existing != event:
                    raise FailureRepairStoreError("E_HISTORY_IDEMPOTENCY_CONFLICT")
                if pending:
                    self._write_projections(events, event["occurred_at"])
                    self.intent_path.unlink(missing_ok=True)
                return {"status": "duplicate", "event_id": existing["event_id"], "event_count": len(events)}
            self._validate_existing_projections(events)
            self._check_repair_gate(event, events)
            intent = {"schema_version": "ui-test.failure-repair-intent.v1", "idempotency_key": event["idempotency_key"], "event_id": event["event_id"], "event_hash": canonical_hash(event)}
            _atomic_json(self.intent_path, intent)
            if fail_after == "intent":
                raise FailureRepairStoreError("E_HISTORY_INJECTED_AFTER_INTENT")
            day_path = self.history_root / f"{event['log_date']}.jsonl"
            day_path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            with day_path.open("ab") as stream:
                stream.write(line.encode("utf-8"))
                stream.flush()
                os.fsync(stream.fileno())
            if fail_after == "append":
                raise FailureRepairStoreError("E_HISTORY_INJECTED_AFTER_APPEND")
            events.append(event)
            self._write_projections(events, event["occurred_at"])
            if fail_after == "projections":
                raise FailureRepairStoreError("E_HISTORY_INJECTED_AFTER_PROJECTIONS")
            self.intent_path.unlink(missing_ok=True)
            readback = self._all_events()
            if not any(item["event_id"] == event["event_id"] for item in readback):
                raise FailureRepairStoreError("E_HISTORY_READBACK_FAILED")
            return {"status": "appended", "event_id": event["event_id"], "event_count": len(readback)}

    def _write_projections(self, events: list[dict[str, Any]], generated_at: str) -> None:
        index, unfinished = self._project(events, generated_at)
        _atomic_json(self.index_path, index)
        _atomic_json(self.unfinished_path, unfinished)
        if load_strict_json(self.index_path) != index or load_strict_json(self.unfinished_path) != unfinished:
            raise FailureRepairStoreError("E_HISTORY_PROJECTION_READBACK_FAILED")

    def rebuild_projections(self, *, generated_at: str | None = None) -> dict[str, Any]:
        """Explicit repair-only operation; normal append never silently rebuilds damage."""
        with exclusive_file_lock(self.lock_path):
            events = self._all_events()
            timestamp = generated_at or datetime.now(CHINA_ZONE).isoformat()
            self._write_projections(events, timestamp)
            return {"status": "rebuilt", "event_count": len(events)}
