"""Internal RFC 8785/JCS boundary for UI-Test JSON identity material."""

from __future__ import annotations

import hashlib
from typing import Any

import rfc8785


RFC8785_IMPLEMENTATION = "rfc8785"
RFC8785_VERSION = "0.1.4"


def dumps(value: Any) -> bytes:
    """Return RFC 8785 canonical JSON bytes through the project wrapper."""
    return rfc8785.dumps(value)


def sha256(value: Any) -> str:
    return "sha256:" + hashlib.sha256(dumps(value)).hexdigest()
