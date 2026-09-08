#!/usr/bin/env python3
"""Small stdio-to-HTTP MCP bridge for Exa.

Claude Code 2.1.178 can start the remote HTTP server but, in this environment,
does not complete the streamable-HTTP negotiation required by Exa.  This
bridge keeps Claude on the standard stdio MCP transport and forwards only the
MCP methods required by the Exa search server.  It does not contain or accept
credentials; Exa's public endpoint is used as configured.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any


EXA_URL = "https://mcp.exa.ai/mcp"
PROTOCOL_VERSION = "2024-11-05"


class BridgeError(RuntimeError):
    pass


class ExaClient:
    def __init__(self) -> None:
        self.session_id: str | None = None

    def request(self, method: str, params: dict[str, Any] | None, request_id: Any) -> dict[str, Any]:
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            payload["params"] = params
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
            "User-Agent": "codex-exa-mcp-bridge/1.0",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        req = urllib.request.Request(EXA_URL, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                if response.headers.get("Mcp-Session-Id"):
                    self.session_id = response.headers["Mcp-Session-Id"]
                raw = response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise BridgeError(f"Exa HTTP request failed: {exc}") from exc
        for line in raw.splitlines():
            if line.startswith("data:"):
                try:
                    result = json.loads(line[5:].strip())
                except json.JSONDecodeError as exc:
                    raise BridgeError(f"Exa returned invalid JSON: {exc}") from exc
                if isinstance(result, dict):
                    return result
        raise BridgeError("Exa returned no JSON-RPC data event")


def send(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def error(request_id: Any, code: int, message: str) -> None:
    send({"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}})


def main() -> int:
    # Claude's stdio transport is UTF-8 even when Windows inherits a GBK
    # console encoding.
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8", errors="strict")
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    client = ExaClient()
    for line in sys.stdin:
        if not line.strip():
            continue
        request_id: Any = None
        try:
            incoming = json.loads(line)
            request_id = incoming.get("id")
            method = incoming.get("method")
            params = incoming.get("params")
            if method == "notifications/initialized" or method == "notifications/cancelled":
                continue
            if method == "initialize":
                result = client.request("initialize", params if isinstance(params, dict) else {}, request_id)
                send(result)
                continue
            if method == "ping":
                result = client.request("ping", {}, request_id)
                send(result)
                continue
            if method in {"tools/list", "tools/call"}:
                result = client.request(method, params if isinstance(params, dict) else {}, request_id)
                send(result)
                continue
            if request_id is not None:
                error(request_id, -32601, f"Unsupported MCP method: {method}")
        except (json.JSONDecodeError, AttributeError) as exc:
            error(request_id, -32700, f"Invalid JSON-RPC request: {exc}")
        except BridgeError as exc:
            error(request_id, -32000, str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
