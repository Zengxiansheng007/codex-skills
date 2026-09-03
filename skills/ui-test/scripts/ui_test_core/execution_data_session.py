"""Frozen parameter session, immutable resolved snapshot and one-shot business-write gate."""

from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from .case_contracts import canonical_hash, validate_document
from .path_utils import canonical_display_path, io_path
from .strict_json import load_strict_json


class ExecutionDataError(RuntimeError):
    """执行参数门禁错误，不回显凭据或参数实际值。"""


@dataclass
class BusinessWritePermit:
    """一次性业务写许可，仅表示参数门禁通过，不替代 R2 授权。"""

    run_id: str
    snapshot_hash: str
    _consumed: bool = False

    def consume(self) -> None:
        if self._consumed:
            raise ExecutionDataError("E_BUSINESS_WRITE_PERMIT_ALREADY_CONSUMED")
        self._consumed = True


class ExecutionDataSession:
    """Freeze one run's inputs and fail closed whenever the editable file drifts."""

    def __init__(
        self,
        *,
        run_id: str,
        build_fingerprint: str,
        test_data_path: str | Path,
        parameter_manifest: dict[str, Any],
        credential_resolver: Callable[[str], Any] | None = None,
        sequence_resolver: Callable[[str], Any] | None = None,
    ) -> None:
        self.run_id = run_id
        self.build_fingerprint = build_fingerprint
        self.test_data_path = io_path(test_data_path)
        self.parameter_manifest = copy.deepcopy(parameter_manifest)
        self.credential_resolver = credential_resolver
        self.sequence_resolver = sequence_resolver
        self._parameters = {item["parameter_id"]: item for item in self.parameter_manifest["parameters"]}
        self._resolved: dict[str, Any] = {}
        self._derived: dict[str, dict[str, Any]] = {}
        self._snapshot_path: Path | None = None
        self._snapshot_hash: str | None = None
        self._started = False

    def _current_test_data_hash(self) -> str:
        return canonical_hash(load_strict_json(self.test_data_path))

    def _check_identity(self) -> None:
        if self._current_test_data_hash() != self.parameter_manifest["test_data_hash"]:
            raise ExecutionDataError("E_EXECUTION_TEST_DATA_DRIFT")

    def start(self) -> None:
        """Call before constructing BrowserContext or opening a page."""
        self._check_identity()
        if canonical_hash({key: value for key, value in self.parameter_manifest.items() if key != "parameter_manifest_hash"}) != self.parameter_manifest["parameter_manifest_hash"]:
            raise ExecutionDataError("E_EXECUTION_PARAMETER_MANIFEST_DRIFT")
        self._started = True

    def consume(self, parameter_id: str) -> Any:
        if not self._started:
            raise ExecutionDataError("E_EXECUTION_DATA_SESSION_NOT_STARTED")
        self._check_identity()
        item = self._parameters.get(parameter_id)
        if item is None:
            raise ExecutionDataError(f"E_EXECUTION_PARAMETER_UNKNOWN:{parameter_id}")
        source_type = item["source_type"]
        if source_type in {"test-data", "value"}:
            value = copy.deepcopy(item["value"])
        elif source_type == "credential":
            if self.credential_resolver is None:
                raise ExecutionDataError("E_EXECUTION_CREDENTIAL_RESOLVER_MISSING")
            # 凭据只在受控进程内存中返回，绝不进入 resolved snapshot。
            value = self.credential_resolver(item["ref"].split(":", 1)[1])
        elif source_type == "sequence":
            if self.sequence_resolver is None:
                raise ExecutionDataError("E_EXECUTION_SEQUENCE_RESOLVER_MISSING")
            value = self.sequence_resolver(item["ref"].split(":", 1)[1])
        else:
            raise ExecutionDataError("E_EXECUTION_PARAMETER_SOURCE_UNKNOWN")
        self._resolved[parameter_id] = value
        return copy.deepcopy(value)

    def record_derived(self, parameter_id: str, value: Any, *, derived_from: list[str]) -> None:
        """Record a non-credential run value produced from governed parameters/rules."""
        if not self._started:
            raise ExecutionDataError("E_EXECUTION_DATA_SESSION_NOT_STARTED")
        self._check_identity()
        if not parameter_id or parameter_id in self._parameters or parameter_id in self._derived:
            raise ExecutionDataError("E_EXECUTION_DERIVED_PARAMETER_ID_INVALID")
        if not derived_from or any(item not in self._parameters for item in derived_from):
            raise ExecutionDataError("E_EXECUTION_DERIVED_SOURCE_INVALID")
        self._derived[parameter_id] = {
            "parameter_id": parameter_id,
            "ref": "derived:" + ",".join(sorted(derived_from)),
            "source_type": "derived",
            "value": copy.deepcopy(value),
        }

    def seal_snapshot(self, path: str | Path, *, sealed_at: str | None = None) -> dict[str, Any]:
        if not self._started:
            raise ExecutionDataError("E_EXECUTION_DATA_SESSION_NOT_STARTED")
        self._check_identity()
        if self._snapshot_path is not None:
            raise ExecutionDataError("E_EXECUTION_SNAPSHOT_ALREADY_SEALED")
        rows: list[dict[str, Any]] = []
        for item in self.parameter_manifest["parameters"]:
            row = {"parameter_id": item["parameter_id"], "ref": item["ref"], "source_type": item["source_type"]}
            if item["source_type"] == "credential":
                row["reference_only"] = True
            elif item["source_type"] == "sequence":
                if item["parameter_id"] not in self._resolved:
                    raise ExecutionDataError(f"E_EXECUTION_SEQUENCE_NOT_CONSUMED:{item['parameter_id']}")
                row["value"] = copy.deepcopy(self._resolved[item["parameter_id"]])
            else:
                row["value"] = copy.deepcopy(item["value"])
            rows.append(row)
        rows.extend(copy.deepcopy(self._derived[key]) for key in sorted(self._derived))
        snapshot = {
            "schema_version": "ui-test.resolved-test-data.v2",
            "run_id": self.run_id,
            "case_id": self.parameter_manifest["case_id"],
            "branch_id": self.parameter_manifest["branch_id"],
            "build_fingerprint": self.build_fingerprint,
            "test_data_hash": self.parameter_manifest["test_data_hash"],
            "parameter_manifest_hash": self.parameter_manifest["parameter_manifest_hash"],
            "parameters": rows,
            "sealed_at": sealed_at or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
        snapshot["snapshot_hash"] = canonical_hash(snapshot)
        if validate_document(snapshot, "resolved-test-data.schema.json"):
            raise ExecutionDataError("E_EXECUTION_SNAPSHOT_SCHEMA_INVALID")
        target = io_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            # 使用独占创建确保同一 Run 的快照不会被覆盖。
            with target.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(snapshot, stream, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError as exc:
            raise ExecutionDataError("E_EXECUTION_SNAPSHOT_EXISTS") from exc
        if load_strict_json(target) != snapshot:
            raise ExecutionDataError("E_EXECUTION_SNAPSHOT_READBACK_FAILED")
        self._snapshot_path = target.resolve()
        self._snapshot_hash = snapshot["snapshot_hash"]
        return copy.deepcopy(snapshot)

    def authorize_business_write(self) -> BusinessWritePermit:
        """Recheck inputs and sealed snapshot immediately before the first business write."""
        self._check_identity()
        if self._snapshot_path is None or self._snapshot_hash is None:
            raise ExecutionDataError("E_EXECUTION_SNAPSHOT_REQUIRED")
        snapshot = load_strict_json(self._snapshot_path)
        supplied_hash = snapshot.get("snapshot_hash")
        computed_hash = canonical_hash({key: value for key, value in snapshot.items() if key != "snapshot_hash"})
        if supplied_hash != self._snapshot_hash or supplied_hash != computed_hash:
            raise ExecutionDataError("E_EXECUTION_SNAPSHOT_DRIFT")
        return BusinessWritePermit(run_id=self.run_id, snapshot_hash=self._snapshot_hash)

    @property
    def snapshot_ref(self) -> str | None:
        return str(canonical_display_path(self._snapshot_path)) if self._snapshot_path else None

    @property
    def snapshot_hash(self) -> str | None:
        return self._snapshot_hash
