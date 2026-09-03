"""Display-path and Windows extended-length I/O path helpers."""

from __future__ import annotations

import os
from pathlib import Path


def canonical_display_path(path: str | Path) -> Path:
    """Return a normal absolute path suitable for manifests and user output."""
    text = str(path)
    if os.name == "nt" and text.startswith("\\\\?\\UNC\\"):
        text = "\\\\" + text[8:]
    elif os.name == "nt" and text.startswith("\\\\?\\"):
        text = text[4:]
    return Path(os.path.abspath(text))


def io_path(path: str | Path) -> Path:
    """Return an extended-length Windows path for all filesystem operations."""
    display = str(canonical_display_path(path))
    if os.name != "nt":
        return Path(display)
    if display.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + display[2:])
    return Path("\\\\?\\" + display)

