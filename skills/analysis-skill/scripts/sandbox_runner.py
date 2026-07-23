#!/usr/bin/env python3
"""R3 sandbox policy gate and Docker-based execution adapter."""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_report(report: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    embedded = json.dumps(report, ensure_ascii=False).replace("</", "<\\/")
    output.write_text(
        f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>R3 隔离执行策略报告</title>
<style>body{{font-family:Microsoft YaHei,Arial,sans-serif;background:#f6f8fb;color:#17202a}}main{{max-width:980px;margin:24px auto;background:#fff;border:1px solid #d8e0e7;padding:28px}}pre{{white-space:pre-wrap;background:#f3f6f9;padding:12px;border:1px solid #d8e0e7}}</style></head>
<body><main><h1>R3 隔离执行策略报告</h1><p>状态：<strong>{html.escape(report['status'])}</strong></p><pre>{html.escape(json.dumps(report, ensure_ascii=False, indent=2))}</pre></main>
<script type="application/json" id="sandbox-runner-report">{embedded}</script></body></html>""",
        encoding="utf-8",
    )


def docker_command(source: Path, output_dir: Path, image: str, command: list[str], network: str) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--network",
        network,
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "-v",
        f"{source.resolve()}:/input:ro",
        "-v",
        f"{output_dir.resolve()}:/output",
        image,
        *command,
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an approved R3 command in an installed sandbox provider")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provider", choices=["docker"], default="docker")
    parser.add_argument("--image", default="python:3.11-slim")
    command_group = parser.add_mutually_exclusive_group(required=True)
    command_group.add_argument("--command-json", help="JSON array command to run inside sandbox")
    command_group.add_argument("--command-file", type=Path, help="JSON file containing the command array")
    parser.add_argument("--network", choices=["none"], default="none")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--allow-r3", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        raw_command = args.command_file.read_text(encoding="utf-8-sig") if args.command_file else args.command_json
        command = json.loads(raw_command)
        if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
            raise ValueError("command-json must be a JSON string array")
        planned = docker_command(args.source, args.output.parent / "_sandbox_output", args.image, command, args.network)
        report: dict[str, Any] = {
            "tool": "analysis-skill.sandbox-runner",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "provider": args.provider,
            "source": str(args.source.resolve()),
            "image": args.image,
            "network": args.network,
            "timeoutSeconds": args.timeout,
            "status": "planned",
            "plannedCommand": ["docker", "run", "...", args.image, *command],
            "policy": "read-only input mount, writable output mount, no network, read-only container filesystem, dropped capabilities",
        }
        if args.dry_run:
            report["status"] = "dry-run"
            write_report(report, args.output)
            print(f"report: {args.output}")
            return 0
        if not args.allow_r3:
            report["status"] = "blocked"
            report["reason"] = "R3 execution requires --allow-r3 after explicit user approval"
            write_report(report, args.output)
            print(f"report: {args.output}")
            return 2
        if not shutil.which("docker"):
            report["status"] = "blocked"
            report["reason"] = "Docker is not installed or not available on PATH"
            write_report(report, args.output)
            print(f"report: {args.output}")
            return 3
        (args.output.parent / "_sandbox_output").mkdir(parents=True, exist_ok=True)
        process = subprocess.run(planned, capture_output=True, text=True, timeout=args.timeout, shell=False)
        report["status"] = "completed"
        report["exitCode"] = process.returncode
        report["stdout"] = process.stdout[:20_000]
        report["stderr"] = process.stderr[:20_000]
        write_report(report, args.output)
        print(f"report: {args.output}")
        return 0 if process.returncode == 0 else 1
    except Exception as error:
        report = {"tool": "analysis-skill.sandbox-runner", "generatedAt": datetime.now(timezone.utc).isoformat(), "status": "failed", "reason": str(error)}
        write_report(report, args.output)
        print(f"sandbox runner failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
