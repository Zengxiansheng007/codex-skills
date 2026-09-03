"""Strict UTF-8 JSON loading with deterministic duplicate-key diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StrictJsonError(ValueError):
    """稳定错误码，不在异常中回显原始值。"""


def _reject_constant(name: str) -> None:
    # JSON 标准不允许 NaN、Infinity 和 -Infinity，必须失败关闭。
    raise StrictJsonError(f"E_JSON_NON_FINITE:{name}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            # 只记录重复键名，不回显对应业务值。
            raise StrictJsonError(f"E_JSON_DUPLICATE_KEY:{key}")
        result[key] = value
    return result


def loads_strict(text: str) -> Any:
    """Parse one strict JSON document."""
    try:
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except StrictJsonError:
        raise
    except json.JSONDecodeError as exc:
        # 仅输出位置和解析原因，不拼接原始文档片段。
        raise StrictJsonError(f"E_JSON_INVALID:{exc.lineno}:{exc.colno}:{exc.msg}") from exc


def load_strict_json(path: str | Path) -> Any:
    """Read strict UTF-8 JSON without accepting a BOM or replacement characters."""
    source = Path(path)
    try:
        raw = source.read_bytes()
    except OSError as exc:
        raise StrictJsonError(f"E_JSON_FILE_UNREADABLE:{exc.__class__.__name__}") from exc
    if raw.startswith(b"\xef\xbb\xbf"):
        raise StrictJsonError("E_JSON_UTF8_BOM_FORBIDDEN")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise StrictJsonError("E_JSON_UTF8_INVALID") from exc
    return loads_strict(text)

