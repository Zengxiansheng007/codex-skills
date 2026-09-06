"""Local evidence checks for Grill protected assets; this is not a global write guard."""

from __future__ import annotations

import hashlib
import os
import re
import stat
from pathlib import Path
from typing import Any, Iterable


class BoundaryError(ValueError):
    """Raised when a supplied path cannot be safely observed in this workspace."""


_VERSION_SUFFIX = re.compile(r"(?:[._-]?(?:v(?:ersion)?)?\d+(?:[._-]\d+)*)$", re.IGNORECASE)  # Covers v2 and v2.1 replacements.
_FILE_ATTRIBUTE_REPARSE_POINT = 0x0400  # Windows junctions are reparse points but are not always Path.is_symlink().


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()  # Content hashes are evidence, not semantic interpretation.
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_reparse_point(path: Path) -> bool:
    """Detect POSIX symlinks and Windows reparse points without following either."""
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return False
    attributes = getattr(metadata, "st_file_attributes", 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & _FILE_ATTRIBUTE_REPARSE_POINT)


def _reject_reparse_point(path: Path, label: str) -> None:
    if _is_reparse_point(path):
        raise BoundaryError(f"{label} is a reparse/symlink entry: {path}")


def _reject_reparse_ancestors(root: Path, candidate: Path) -> None:
    """Reject a junction/symlink before resolve can hide the entry being inspected."""
    try:
        lexical = candidate.absolute()
        relative = lexical.relative_to(root)
    except ValueError as exc:
        raise BoundaryError(f"path escapes workspace root: {candidate}") from exc
    current = root
    _reject_reparse_point(current, "workspace root")
    for part in relative.parts:
        current = current / part
        if os.path.lexists(current):
            _reject_reparse_point(current, "workspace path component")


def normalize_workspace_path(workspace_root: str | Path, supplied_path: str | Path) -> Path:
    """Resolve one path and reject traversal, outside-root, and reparse-point escapes."""
    lexical_root = Path(workspace_root).absolute()
    _reject_reparse_point(lexical_root, "workspace root")
    root = lexical_root.resolve(strict=True)
    raw = Path(supplied_path)
    if ".." in raw.parts:
        raise BoundaryError(f"parent traversal is not allowed: {supplied_path}")
    candidate = raw if raw.is_absolute() else root / raw
    _reject_reparse_ancestors(root, candidate)
    resolved = candidate.resolve(strict=False)  # Existing symlinks/reparse points are collapsed here.
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise BoundaryError(f"path escapes workspace root: {supplied_path}") from exc
    return resolved


def relative_workspace_path(workspace_root: str | Path, supplied_path: str | Path) -> str:
    root = Path(workspace_root).resolve(strict=True)
    return normalize_workspace_path(root, supplied_path).relative_to(root).as_posix()


def _version_identity(path: Path) -> str:
    return _VERSION_SUFFIX.sub("", path.stem).casefold() + path.suffix.casefold()


def _iter_file_scope(root: Path, path: Path) -> Iterable[Path]:
    """Observe the protected file and same-directory version replacements."""
    _reject_reparse_point(path, "protected file")
    if path.exists() and path.is_file():
        yield path
    parent = path.parent
    _reject_reparse_point(parent, "protected file parent")
    if parent.is_dir():
        identity = _version_identity(path)
        for sibling in parent.iterdir():
            if _version_identity(sibling) == identity:
                _reject_reparse_point(sibling, "protected version sibling")
            if sibling.is_file() and _version_identity(sibling) == identity:
                yield sibling  # New v2/v3 siblings cannot bypass a protected formal file.


def _scope_paths(workspace_root: Path, scope: dict[str, Any]) -> Iterable[Path]:
    target = normalize_workspace_path(workspace_root, scope["path"])
    kind = scope.get("kind", "file")
    if kind == "file":
        yield from _iter_file_scope(workspace_root, target)
        return
    if kind != "directory":
        raise BoundaryError(f"unknown protected scope kind: {kind}")
    if target.exists() and not target.is_dir():
        raise BoundaryError(f"directory scope is not a directory: {scope['path']}")
    if target.exists():
        _reject_reparse_point(target, "protected directory")
        for current, dirs, files in os.walk(target, followlinks=False):
            current_path = Path(current)
            _reject_reparse_point(current_path, "protected directory descendant")
            reparse_dirs = [name for name in dirs if _is_reparse_point(current_path / name)]
            if reparse_dirs:
                raise BoundaryError(f"protected directory contains reparse/symlink entries: {', '.join(reparse_dirs)}")
            for name in files:
                file_path = current_path / name
                _reject_reparse_point(file_path, "protected directory file")
                yield file_path


def snapshot_protected_assets(workspace_root: str | Path, scopes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return an absolute-root-normalized manifest for every observable protected file."""
    lexical_root = Path(workspace_root).absolute()
    _reject_reparse_point(lexical_root, "workspace root")
    root = lexical_root.resolve(strict=True)
    snapshot: dict[str, dict[str, Any]] = {}
    for scope in scopes:
        for path in _scope_paths(root, scope):
            normalized = normalize_workspace_path(root, path)
            _reject_reparse_point(normalized, "protected snapshot file")
            key = normalized.relative_to(root).as_posix()
            snapshot[key] = {"sha256": _sha256(normalized), "scope": scope["path"]}
    return dict(sorted(snapshot.items()))


def diff_snapshots(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    """Record additions, removals and content changes without claiming semantic meaning."""
    changes = []
    for path in sorted(set(before) | set(after)):
        if path not in before:
            changes.append({"path": path, "kind": "added"})
        elif path not in after:
            changes.append({"path": path, "kind": "deleted"})
        elif before[path]["sha256"] != after[path]["sha256"]:
            changes.append({"path": path, "kind": "modified"})
    return changes


def scope_contains(workspace_root: str | Path, scopes: list[dict[str, Any]], supplied_path: str | Path) -> bool:
    """Return whether a write target is explicitly allowed by a normalized scope."""
    root = Path(workspace_root).resolve(strict=True)
    target = normalize_workspace_path(root, supplied_path)
    for scope in scopes:
        scope_path = normalize_workspace_path(root, scope["path"])
        if scope.get("kind", "file") == "directory":
            try:
                target.relative_to(scope_path)
                return True
            except ValueError:
                continue
        if target == scope_path:
            return True
    return False


def verify_expected_postconditions(workspace_root: str | Path, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Hash actual target contents; receipt claims alone never prove completion."""
    root = Path(workspace_root).resolve(strict=True)
    results = []
    for item in items:
        target = normalize_workspace_path(root, item["path"])
        expected = item.get("expectedSha256")
        if not isinstance(expected, str) or len(expected) != 64:
            results.append({"id": item.get("id"), "path": str(item.get("path")), "status": "invalid-expected-hash"})
            continue
        if not target.is_file():
            results.append({"id": item.get("id"), "path": relative_workspace_path(root, target), "status": "missing"})
            continue
        actual = _sha256(target)
        results.append({
            "id": item.get("id"),
            "path": relative_workspace_path(root, target),
            "status": "verified" if actual == expected else "hash-mismatch",
            "actualSha256": actual,
        })
    return results
