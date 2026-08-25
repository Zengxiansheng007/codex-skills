from __future__ import annotations

from typing import Any

from .models import FAILURE_LAYERS, FAILURE_TYPES


def failure_attribution(layer: str, failure_type: str, detail: str, **extra: Any) -> dict[str, Any]:
    """Build machine-readable failure attribution for runtime reports."""
    normalized_layer = layer if layer in FAILURE_LAYERS else "runtime"
    normalized_type = failure_type if failure_type in FAILURE_TYPES else "unknown"
    payload: dict[str, Any] = {
        "layer": normalized_layer,
        "failure_type": normalized_type,
        "detail": detail,
        "confidence": 1.0,
    }
    payload.update(extra)
    return payload
