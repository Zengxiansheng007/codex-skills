"""Boundary tests for actual temporary files, paths, version names, and reparse entries."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from grill_artifact_checks import BoundaryError, normalize_workspace_path, snapshot_protected_assets


def test_paths_and_semver_versions(tmp: Path) -> None:
    formal = tmp / "formal"; formal.mkdir()
    (formal / "requirements-prd-v0.1.md").write_text("one", encoding="utf-8")
    (formal / "requirements-prd-v2.1.md").write_text("two", encoding="utf-8")
    snapshot = snapshot_protected_assets(tmp, [{"path": "formal/requirements-prd-v0.1.md", "kind": "file"}])
    assert set(snapshot) == {"formal/requirements-prd-v0.1.md", "formal/requirements-prd-v2.1.md"}
    for unsafe in ("../outside.md", str(tmp.parent / "outside.md")):
        try:
            normalize_workspace_path(tmp, unsafe)
        except BoundaryError:
            pass
        else:
            raise AssertionError("outside path must fail closed")


def test_reparse_escape_fails_closed(tmp: Path) -> None:
    workspace = tmp / "workspace"; workspace.mkdir()
    formal = workspace / "formal"; formal.mkdir()
    target = formal / "requirements-prd-v0.1.md"; target.write_text("one", encoding="utf-8")
    outside = tmp / "outside-target.txt"; outside.write_text("outside", encoding="utf-8")
    link = formal / "requirements-prd-v2.1.md"
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        print("  SKIP: symlink creation is unavailable on this Windows account")
        return
    try:
        snapshot_protected_assets(workspace, [{"path": "formal/requirements-prd-v0.1.md", "kind": "file"}])
    except BoundaryError:
        pass
    else:
        raise AssertionError("protected reparse/symlink sibling must fail closed")


def test_windows_junction_fails_closed(tmp: Path) -> None:
    workspace = tmp / "workspace"; workspace.mkdir()
    protected = workspace / "formal"; protected.mkdir()
    outside = tmp / "outside"; outside.mkdir()
    (outside / "external.md").write_text("outside", encoding="utf-8")
    junction = protected / "junction"
    result = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(outside)], text=True, capture_output=True, check=False)
    if result.returncode != 0:
        print("  SKIP: junction creation is unavailable on this Windows account")
        return
    attributes = os.lstat(junction).st_file_attributes
    assert attributes & 0x0400, f"expected FILE_ATTRIBUTE_REPARSE_POINT, got {attributes}"
    try:
        snapshot_protected_assets(workspace, [{"path": "formal", "kind": "directory"}])
    except BoundaryError:
        pass
    else:
        raise AssertionError("protected directory junction must fail closed")


if __name__ == "__main__":
    for test in (test_paths_and_semver_versions, test_reparse_escape_fails_closed, test_windows_junction_fails_closed):
        with tempfile.TemporaryDirectory() as directory:
            test(Path(directory))
    print("ok: Grill artifact boundary tests passed")
