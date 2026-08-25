"""RFC 9457-style, redacted problem details for UI-Test routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Problem:
    code: str
    title: str
    status: int = 400
    detail: str = ""
    instance: str = ""
    errors: tuple[dict[str, str], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": f"https://codex.local/problems/{self.code.lower()}",
            "title": self.title,
            "status": self.status,
            "code": self.code,
        }
        if self.detail:
            result["detail"] = self.detail
        if self.instance:
            result["instance"] = self.instance
        if self.errors:
            result["errors"] = list(self.errors)
        return result


def from_validation_errors(errors: list[dict[str, str]], instance: str = "") -> Problem:
    return Problem(
        code=errors[0]["code"] if errors else "E_PACKET_INVALID",
        title="UI-Test packet validation failed",
        status=422,
        detail="One or more packet contract checks failed.",
        instance=instance,
        errors=tuple({"code": item["code"], "path": item["path"]} for item in errors),
    )
