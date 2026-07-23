#!/usr/bin/env python3
"""Run optional third-party Skill validators with strict timeouts and explicit uncertainty."""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_OUTPUT = 20_000


def clipped(value: str) -> str:
    text = value[:MAX_OUTPUT]
    return text + ("\n[output truncated]" if len(value) > MAX_OUTPUT else "")


def redact(value: str) -> str:
    import re

    value = re.sub(r"sk-[A-Za-z0-9_-]{20,}", "sk-***REDACTED***", value)
    value = re.sub(r"Bearer\s+[A-Za-z0-9._-]+", "Bearer ***REDACTED***", value, flags=re.I)
    value = re.sub(r"(?i)(password|token|cookie)\s*[:=]\s*\S+", r"\1=***REDACTED***", value)
    return value


def run_command(command: list[str], timeout: int) -> dict[str, Any]:
    try:
        process = subprocess.run(command, capture_output=True, text=True, timeout=timeout, shell=False)
        return {
            "status": "completed",
            "exitCode": process.returncode,
            "stdout": redact(clipped(process.stdout)),
            "stderr": redact(clipped(process.stderr)),
        }
    except subprocess.TimeoutExpired as error:
        return {
            "status": "unverified",
            "reason": f"timeout after {timeout}s",
            "stdout": redact(clipped(error.stdout or "")),
            "stderr": redact(clipped(error.stderr or "")),
        }
    except OSError as error:
        return {"status": "unverified", "reason": str(error)}


def cisco_scan(source: Path, scanner: str | None, timeout: int, output_dir: Path) -> dict[str, Any]:
    executable = scanner or shutil.which("skill-scanner")
    if not executable:
        return {"adapter": "cisco-ai-skill-scanner", "status": "unverified", "reason": "skill-scanner executable not found"}
    output_json = output_dir / "cisco-skill-scanner.json"
    command = [executable, "scan", str(source), "--format", "json", "--output-json", str(output_json), "--policy", "balanced"]
    result = run_command(command, timeout)
    result.update({"adapter": "cisco-ai-skill-scanner", "command": "skill-scanner scan <source> --format json --output-json <file> --policy balanced"})
    if output_json.exists():
        try:
            result["reportJson"] = json.loads(output_json.read_text(encoding="utf-8"))
        except Exception as error:
            result["reportReadError"] = str(error)
    return result


def unavailable(name: str, reason: str) -> dict[str, Any]:
    return {"adapter": name, "status": "unverified", "reason": reason}


def write_reports(report: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    embedded = json.dumps(report, ensure_ascii=False).replace("</", "<\\/")
    rows = ""
    for item in report["adapters"]:
        rows += (
            f"<tr><td>{html.escape(item['adapter'])}</td><td>{html.escape(str(item.get('status')))}</td>"
            f"<td>{html.escape(str(item.get('exitCode', '')))}</td><td>{html.escape(str(item.get('reason', '')))}</td></tr>"
        )
    output.write_text(
        f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>第三方 Skill 检查报告</title>
<style>body{{font-family:Microsoft YaHei,Arial,sans-serif;background:#f6f8fb;color:#17202a}}main{{max-width:1100px;margin:24px auto;background:#fff;border:1px solid #d8e0e7;padding:28px}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #d8e0e7;padding:8px;text-align:left;vertical-align:top}}th{{background:#eef3f8}}.note{{background:#fff8e1;border-left:4px solid #f0ad00;padding:12px}}</style></head>
<body><main><h1>第三方 Validator / Scanner Adapter 报告</h1><div class="note">第三方扫描结果只作为补充证据；不可用、超时或无发现都不能单独证明 Skill 安全。</div>
<table><thead><tr><th>Adapter</th><th>状态</th><th>退出码</th><th>说明</th></tr></thead><tbody>{rows}</tbody></table></main>
<script type="application/json" id="third-party-checks">{embedded}</script></body></html>""",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run optional third-party skill checks")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scanner", help="path to Cisco skill-scanner executable")
    parser.add_argument("--timeout", type=int, default=45)
    args = parser.parse_args(argv)
    work = args.output.parent / "_third_party"
    work.mkdir(parents=True, exist_ok=True)
    report = {
        "tool": "analysis-skill.third-party-checks",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": str(args.source.resolve()),
        "adapters": [
            cisco_scan(args.source, args.scanner, args.timeout, work),
            unavailable("skill-validator", "Go or a pinned skill-validator binary is not installed in this environment"),
            unavailable("skills-ref", "not enabled as a production dependency; demo/reference-only status remains unverified"),
        ],
    }
    write_reports(report, args.output)
    print(f"report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
