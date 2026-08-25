#!/usr/bin/env python3
"""Generate governed UI automation execution reports."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any


SENSITIVE_KEYS = {
    "password",
    "passwd",
    "authorization",
    "cookie",
    "set-cookie",
    "token",
    "secret",
    "api_key",
    "x-token",
}


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("input root must be a JSON object")
    return data


def ensure_required(data: dict[str, Any]) -> None:
    for key in ("report", "grouping", "safety", "steps", "run_result"):
        if key not in data:
            raise ValueError(f"missing required root field: {key}")
    if not isinstance(data["steps"], list) or not data["steps"]:
        raise ValueError("steps must be a non-empty array")
    for field in ("report_id", "run_id", "case_id", "case_name", "status", "execution_date"):
        if not data["report"].get(field):
            raise ValueError(f"missing report.{field}")
    for field in ("project_group", "project", "module", "project_group_slug", "project_slug", "module_slug"):
        if not data["grouping"].get(field):
            raise ValueError(f"missing grouping.{field}")
    for step in data["steps"]:
        for field in ("step_id", "action", "expected_result", "actual_result", "status"):
            if not step.get(field):
                raise ValueError(f"missing steps[].{field}")
        if step.get("ui_changing") and not step.get("ui_evidence"):
            raise ValueError(f"{step['step_id']} is UI-changing but has no ui_evidence")


def build_canonical_run_result(data: dict[str, Any]) -> dict[str, Any]:
    """Read and validate the sole result fact source without recalculating status."""
    run_result = data.get("run_result")
    if not isinstance(run_result, dict) or run_result.get("schema_version") != "ui-test.run-result.v2":
        raise ValueError("run_result must be canonical ui-test.run-result.v2")
    required = ("run_id", "case_id", "branch_id", "overall_status", "step_results", "evidence_refs", "run_result_hash")
    missing = [field for field in required if field not in run_result]
    if missing:
        raise ValueError("run_result missing fields: " + ", ".join(missing))
    if run_result["run_id"] != data["report"]["run_id"] or run_result["case_id"] != data["report"]["case_id"]:
        raise ValueError("report identity differs from canonical run_result")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(run_result["run_result_hash"])):
        raise ValueError("run_result_hash is invalid")
    return json.loads(json.dumps(run_result, ensure_ascii=False))


def scan_sensitive(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_lower = str(key).lower()
            if key_lower in SENSITIVE_KEYS and child not in (None, "", [], {}, True, False):
                findings.append(f"{path}.{key}")
            findings.extend(scan_sensitive(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            findings.extend(scan_sensitive(child, f"{path}[{idx}]"))
    return findings


def e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def json_block(value: Any) -> str:
    return e(json.dumps(value, ensure_ascii=False, indent=2))


def status_badge(status: str) -> str:
    cls = "passed" if status == "passed" else "blocked" if status in {"failed", "blocked"} else "warning"
    return f'<span class="status {cls}">{e(status)}</span>'


def svg(kind: str, large: bool) -> str:
    scale = 640 if large else 320
    height = 360 if large else 180
    if kind == "login":
        return f'''<svg viewBox="0 0 640 360" role="img" aria-label="登录页截图">
  <rect width="640" height="360" fill="#f4f7fb"></rect>
  <rect x="170" y="56" width="300" height="248" rx="10" fill="#ffffff" stroke="#ccd6e3"></rect>
  <text x="320" y="92" text-anchor="middle" font-size="20" fill="#1769e0">运维管理平台</text>
  <rect x="215" y="128" width="210" height="34" rx="4" fill="#f8fafc" stroke="#cfd8e3"></rect>
  <text x="228" y="150" font-size="13" fill="#667085">请输入账号名称</text>
  <rect x="215" y="176" width="210" height="34" rx="4" fill="#f8fafc" stroke="#cfd8e3"></rect>
  <text x="228" y="198" font-size="13" fill="#667085">请输入密码</text>
  <rect x="215" y="228" width="210" height="38" rx="5" fill="#1769e0"></rect>
  <text x="320" y="252" text-anchor="middle" font-size="14" fill="#ffffff">登录</text>
</svg>'''.replace('viewBox="0 0 640 360"', f'viewBox="0 0 640 360" width="{scale}" height="{height}"')
    if kind == "home":
        return f'''<svg viewBox="0 0 640 360" width="{scale}" height="{height}" role="img" aria-label="首页截图">
  <rect width="640" height="360" fill="#eef2f7"></rect><rect width="640" height="46" fill="#1769e0"></rect>
  <text x="22" y="29" font-size="15" fill="#fff">津心办 | 一体化运营平台</text>
  <rect x="0" y="46" width="126" height="314" fill="#ffffff" stroke="#d8dee8"></rect>
  <rect x="150" y="74" width="450" height="210" rx="8" fill="#ffffff" stroke="#d8dee8"></rect>
  <text x="172" y="112" font-size="18" fill="#172033">首页</text>
</svg>'''
    if kind == "module":
        return f'''<svg viewBox="0 0 640 360" width="{scale}" height="{height}" role="img" aria-label="公告管理页截图">
  <rect width="640" height="360" fill="#f5f7fb"></rect><rect width="640" height="44" fill="#1769e0"></rect>
  <rect x="0" y="44" width="130" height="316" fill="#ffffff" stroke="#d8dee8"></rect>
  <rect x="154" y="72" width="456" height="242" rx="8" fill="#ffffff" stroke="#d8dee8"></rect>
  <text x="176" y="105" font-size="16" fill="#172033">公告管理</text>
  <rect x="516" y="86" width="64" height="30" rx="5" fill="#1769e0"></rect><text x="548" y="106" text-anchor="middle" font-size="13" fill="#fff">创建</text>
</svg>'''
    if kind == "form":
        return f'''<svg viewBox="0 0 640 360" width="{scale}" height="{height}" role="img" aria-label="表单截图">
  <rect width="640" height="360" fill="#f6f7f9"></rect><rect x="128" y="30" width="384" height="300" rx="8" fill="#ffffff" stroke="#d8dee8"></rect>
  <text x="152" y="64" font-size="15" fill="#172033">新建公告</text>
  <text x="154" y="104" font-size="12" fill="#263348">公告标题</text><rect x="240" y="86" width="226" height="28" rx="4" fill="#f8fafc" stroke="#ccd6e3"></rect>
  <text x="250" y="105" font-size="11" fill="#263348">0813全体+全省系统公告123</text>
  <text x="154" y="230" font-size="12" fill="#263348">有效期</text><rect x="240" y="212" width="226" height="28" rx="4" fill="#f8fafc" stroke="#ccd6e3"></rect>
  <text x="250" y="231" font-size="11" fill="#263348">2026/08/13 - 2026/08/14</text>
</svg>'''
    if kind == "before-submit":
        return f'''<svg viewBox="0 0 640 360" width="{scale}" height="{height}" role="img" aria-label="提交前截图">
  <rect width="640" height="360" fill="#f6f7f9"></rect><rect x="126" y="34" width="388" height="292" rx="8" fill="#ffffff" stroke="#d8dee8"></rect>
  <text x="154" y="70" font-size="15" fill="#172033">提交前检查</text><text x="154" y="116" font-size="13" fill="#263348">标题：0813全体+全省系统公告123</text>
  <text x="154" y="218" font-size="13" fill="#263348">失效日期：2026-08-14</text><rect x="242" y="260" width="68" height="32" rx="5" fill="#1769e0"></rect>
  <text x="276" y="281" text-anchor="middle" font-size="13" fill="#fff">确认</text>
</svg>'''
    return f'''<svg viewBox="0 0 640 360" width="{scale}" height="{height}" role="img" aria-label="提交后截图">
  <rect width="640" height="360" fill="#f5f7fb"></rect><rect x="160" y="50" width="320" height="38" rx="6" fill="#eaf8f0" stroke="#9bd6b3"></rect>
  <text x="320" y="74" text-anchor="middle" font-size="14" fill="#168a4a">创建成功</text>
  <rect x="80" y="118" width="480" height="176" rx="8" fill="#ffffff" stroke="#d8dee8"></rect>
  <text x="104" y="154" font-size="14" fill="#172033">公告列表</text>
  <text x="104" y="210" font-size="13" fill="#263348">0813全体+全省系统公告123</text>
</svg>'''


def ui_cell(step: dict[str, Any]) -> str:
    ev = step.get("ui_evidence")
    if not ev:
        return e(step.get("ui_missing_reason", "无"))
    kind = ev.get("svg_kind", "after-submit")
    return f'''<details class="cell-detail">
  <summary class="ui-shot-summary">截图缩略图（点击放大）{svg(kind, False)}</summary>
  <div class="shot-large">{svg(kind, True)}
    <div class="path-caption">{e(ev.get("path"))}</div>
    <pre><code>{json_block(ev)}</code></pre>
  </div>
</details>'''


def api_cell(step: dict[str, Any]) -> str:
    api = step.get("api_assertion")
    if not api:
        return e(step.get("api_missing_reason", "无"))
    return f'''<details class="cell-detail api-cell">
  <summary>{e(api.get("api_assertion_id"))}（点击查看 JSON）</summary>
  <pre><code>{json_block(api)}</code></pre>
</details>'''


def collect_attachments(data: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for step in data["steps"]:
        sid = step["step_id"]
        ev = step.get("ui_evidence")
        if ev:
            rows.append({
                "id": ev.get("attachment_id", ev.get("evidence_id", "")),
                "step": sid,
                "type": "image/png",
                "path": ev.get("path", ""),
                "entry": f"第 4 章 {sid} / UI 图片",
                "purpose": "截图完整性、脱敏校验"
            })
        api = step.get("api_assertion")
        if api:
            rows.append({
                "id": api.get("api_assertion_id", ""),
                "step": sid,
                "type": "application/json",
                "path": api.get("raw_ref", ""),
                "entry": f"第 4 章 {sid} / 接口断言",
                "purpose": "接口断言与 JSONPath 校验"
            })
    return rows


def render_html(data: dict[str, Any]) -> str:
    report = data["report"]
    grouping = data["grouping"]
    safety = data["safety"]
    attachment_rows = collect_attachments(data)
    api_rows = [s["api_assertion"] | {"step_id": s["step_id"]} for s in data["steps"] if s.get("api_assertion")]
    step_rows = "\n".join(
        f'''<tr>
  <td>{e(s["step_id"])}</td><td>{e(s["action"])}</td><td>{e(s["expected_result"])}</td><td>{e(s["actual_result"])}</td>
  <td>{status_badge(s["status"])}</td><td class="ui-cell">{ui_cell(s)}</td><td>{api_cell(s)}</td><td>{e(s.get("warning_ref", "无"))}</td>
</tr>'''
        for s in data["steps"]
    )
    attachment_table = "\n".join(
        f'<tr><td>{e(r["id"])}</td><td>{e(r["step"])}</td><td>{e(r["type"])}</td><td>{e(r["path"])}</td><td>{e(r["entry"])}</td><td>{e(r["purpose"])}</td></tr>'
        for r in attachment_rows
    )
    api_table = "\n".join(
        f'<tr><td>{e(a["api_assertion_id"])}</td><td>{e(a["step_id"])}</td><td>{e(a["method"])}</td><td>{e(a["url_template"])}</td><td>{e(a["http_status"])}</td><td>{e(a.get("business_code", ""))}</td><td>{e(a.get("duration_ms", ""))} ms</td><td>{status_badge(a.get("assertion_status", ""))}</td></tr>'
        for a in api_rows
    )
    failures = data.get("failures", [])
    failure_table = "\n".join(
        f'<tr><td>{e(f["failure_id"])}</td><td>{e(f["step_id"])}</td><td>{e(f["layer"])}</td><td>{e(f["category"])}</td><td>{e(f["root_cause_status"])}</td><td>{e(f["summary"])}</td><td>{e(f["impact"])}</td><td>{e(f["next_step"])}</td></tr>'
        for f in failures
    ) or '<tr><td colspan="8">无</td></tr>'
    score_items = data.get("score", {}).get("items", [])
    score_html = "\n".join(
        f'<div class="score"><span>{e(i["name"])}</span><div class="bar"><span style="width:{int(i["score"] / i["max"] * 100)}%"></span></div><strong>{e(i["score"])}/{e(i["max"])}</strong></div>'
        for i in score_items
    )
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{e(grouping["project"])}-{e(report["case_name"])} UI 自动化执行报告</title>
  <style>
    :root {{ --bg:#f6f7f9; --panel:#fff; --ink:#172033; --muted:#5f6b7a; --line:#d8dee8; --brand:#1769e0; --ok:#168a4a; --warn:#a16207; --bad:#b42318; --code:#101828; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--ink); font-family:"Microsoft YaHei","Segoe UI",Arial,sans-serif; line-height:1.55; }}
    header {{ background:#fff; border-bottom:1px solid var(--line); padding:24px 32px 18px; position:sticky; top:0; z-index:10; }}
    main {{ max-width:1280px; margin:22px auto 48px; padding:0 24px; }}
    h1 {{ margin:0 0 10px; font-size:24px; }} h2 {{ margin:0 0 14px; font-size:18px; }} h3 {{ margin:18px 0 10px; font-size:15px; }}
    section {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:20px; margin-bottom:18px; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; }} th,td {{ border:1px solid var(--line); padding:9px 10px; text-align:left; vertical-align:top; }} th {{ background:#f1f4f8; }}
    .steps-table {{ table-layout:fixed; }} .steps-table th:nth-child(1){{width:58px}} .steps-table th:nth-child(2){{width:118px}} .steps-table th:nth-child(3),.steps-table th:nth-child(4){{width:150px}} .steps-table th:nth-child(5){{width:92px}} .steps-table th:nth-child(6){{width:190px}} .steps-table th:nth-child(7){{width:250px}} .steps-table th:nth-child(8){{width:130px}}
    .status {{ display:inline-block; border-radius:999px; padding:2px 9px; font-size:12px; font-weight:700; white-space:nowrap; }} .passed{{background:#eaf8f0;color:var(--ok)}} .warning{{background:#fff7df;color:var(--warn)}} .blocked{{background:#fff0ee;color:var(--bad)}}
    .tag {{ display:inline-block; border:1px solid #c8d5e6; border-radius:999px; background:#f8fbff; padding:2px 8px; margin:2px 3px 2px 0; font-size:12px; }}
    .toc {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; }} .toc a {{ color:var(--brand); text-decoration:none; border:1px solid #bcd4f6; border-radius:999px; padding:4px 10px; font-size:13px; background:#f7fbff; }}
    .notice {{ padding:10px 12px; background:#fff7df; color:#754d00; border:1px solid #f4d06f; border-radius:6px; margin-top:10px; font-size:13px; }}
    .meta-grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin-top:12px; }} .metric {{ border:1px solid var(--line); border-radius:8px; background:#fbfcfe; padding:12px; min-height:78px; }} .metric strong {{ display:block; font-size:12px; color:var(--muted); margin-bottom:6px; }} .metric span {{ font-size:18px; font-weight:700; }}
    details {{ border:1px solid var(--line); border-radius:8px; margin:0; background:#fbfcfe; }} summary {{ cursor:pointer; padding:7px; font-weight:700; color:var(--brand); }}
    .ui-shot-summary svg {{ display:block; width:100%; height:auto; margin-top:6px; border:1px solid var(--line); border-radius:6px; background:#fff; }}
    .shot-large {{ padding:8px; border-top:1px solid var(--line); }} .shot-large svg {{ display:block; width:min(720px,100%); height:auto; border:1px solid var(--line); border-radius:6px; background:#fff; }}
    .path-caption {{ color:var(--muted); font-size:13px; line-height:1.65; word-break:break-all; }}
    pre {{ margin:0; padding:12px; overflow-x:auto; background:var(--code); color:#e6edf7; font-size:11px; line-height:1.5; max-height:280px; }} code {{ font-family:Consolas,"Courier New",monospace; }}
    .score {{ display:grid; grid-template-columns:180px 1fr 60px; gap:10px; align-items:center; margin:8px 0; font-size:13px; }} .bar {{ height:10px; border-radius:999px; background:#e7ebf2; overflow:hidden; }} .bar>span {{ display:block; height:100%; background:var(--ok); }}
    @media (max-width:900px) {{ header{{position:static;padding:18px}} main{{padding:0 14px}} .meta-grid{{grid-template-columns:1fr}} table{{font-size:12px}} }}
  </style>
</head>
<body>
<header>
  <h1>{e(grouping["project"])}-{e(report["case_name"])} UI 自动化执行报告</h1>
  <div>{status_badge(report["status"])} <span class="tag">{e(grouping["project_group"])}</span><span class="tag">{e(grouping["project"])}</span><span class="tag">{e(grouping["module"])}</span><span class="tag">{e(report["execution_date"])}</span></div>
  <div class="notice">本报告按 A 方案生成：截图与 JSON/接口详情直接嵌入第 4 章步骤表；第 5 章仅为附件索引。</div>
  <nav class="toc"><a href="#summary">执行摘要</a><a href="#steps">用例步骤</a><a href="#attachments">附件索引</a><a href="#api">接口索引</a><a href="#failure">归因</a><a href="#score">评分</a><a href="#promotion">晋级</a></nav>
</header>
<main>
<section id="summary"><h2>1. 执行摘要</h2><div class="meta-grid"><div class="metric"><strong>报告 ID</strong><span>{e(report["report_id"])}</span></div><div class="metric"><strong>Run ID</strong><span>{e(report["run_id"])}</span></div><div class="metric"><strong>最终状态</strong>{status_badge(report["status"])}</div><div class="metric"><strong>证据评分</strong><span>{e(data.get("score", {}).get("total", ""))}/100</span></div></div><table style="margin-top:14px"><tbody><tr><th>用例 ID</th><td>{e(report["case_id"])}</td><th>用例名称</th><td>{e(report["case_name"])}</td></tr><tr><th>执行器</th><td>{e(report.get("executor"))}</td><th>环境</th><td>{e(report.get("environment"))}</td></tr><tr><th>一句话结论</th><td colspan="3">{e(report.get("summary"))}</td></tr></tbody></table></section>
<section id="safety"><h2>2. 范围与安全边界</h2><table><tbody><tr><th>允许动作</th><td>{e(safety.get("allowed_actions"))}</td></tr><tr><th>禁止动作</th><td>{e(safety.get("forbidden_actions"))}</td></tr><tr><th>账号类型</th><td>{e(safety.get("account_type"))}</td></tr><tr><th>外部模型边界</th><td>{e(safety.get("model_boundary"))}</td></tr><tr><th>敏感信息处理</th><td>{e(safety.get("redaction"))}</td></tr></tbody></table></section>
<section id="steps"><h2>4. 功能测试用例步骤与执行结果</h2><table class="steps-table"><thead><tr><th>Step</th><th>动作</th><th>期望结果</th><th>实际结果</th><th>状态</th><th>UI 图片</th><th>接口断言</th><th>失败/告警</th></tr></thead><tbody>{step_rows}</tbody></table></section>
<section id="attachments"><h2>5. 附件索引（治理用）</h2><p>人读主入口已前移到第 4 章步骤表。本章仅保留附件路径和治理索引。</p><table><thead><tr><th>Attachment ID</th><th>Step</th><th>类型</th><th>路径</th><th>人读入口</th><th>治理用途</th></tr></thead><tbody>{attachment_table}</tbody></table></section>
<section id="api"><h2>6. 接口汇总索引（治理用）</h2><p>接口 JSON 详情已直接嵌入第 4 章对应 Step 的“接口断言”单元格。</p><table><thead><tr><th>断言 ID</th><th>Step</th><th>Method</th><th>URL Template</th><th>HTTP</th><th>业务码</th><th>耗时</th><th>状态</th></tr></thead><tbody>{api_table}</tbody></table></section>
<section id="failure"><h2>9. 失败与告警归因</h2><table><thead><tr><th>Failure ID</th><th>Step</th><th>层级</th><th>分类</th><th>根因状态</th><th>根因摘要</th><th>影响</th><th>下一步</th></tr></thead><tbody>{failure_table}</tbody></table></section>
<section id="score"><h2>10. 证据完整性评分</h2>{score_html}<p><strong>合计：{e(data.get("score", {}).get("total", ""))}/100。</strong></p></section>
<section id="promotion"><h2>11. 结论与晋级建议</h2><table><tbody><tr><th>是否可晋级 Playwright 回归</th><td>{e(data.get("promotion", {}).get("playwright"))}</td></tr><tr><th>是否可晋级 checkpoint</th><td>{e(data.get("promotion", {}).get("checkpoint"))}</td></tr><tr><th>是否可晋级 Memory</th><td>{e(data.get("promotion", {}).get("memory"))}</td></tr><tr><th>晋级理由</th><td>{e(data.get("promotion", {}).get("reason"))}</td></tr></tbody></table></section>
<script type="application/json" id="report-evidence-index">{json_block(build_evidence_index(data, ""))}</script>
</main>
</body>
</html>'''


def build_evidence_index(data: dict[str, Any], report_path: str) -> dict[str, Any]:
    return {
        "schema_version": "ui-test-execution-report.v1",
        "report_id": data["report"]["report_id"],
        "run_id": data["report"]["run_id"],
        "source_run_result_hash": data["run_result"]["run_result_hash"],
        "human_report_path": report_path,
        "layout_contract": "step-table-embedded-evidence",
        "steps": [
            {
                "step_id": s["step_id"],
                "status": s["status"],
                "ui_evidence_ref": s.get("ui_evidence", {}).get("attachment_id"),
                "api_assertion_ref": s.get("api_assertion", {}).get("api_assertion_id"),
                "human_entry": f"report.html#steps:{s['step_id']}"
            }
            for s in data["steps"]
        ],
        "attachments": collect_attachments(data)
    }


def build_execution_summary(data: dict[str, Any], report_path: str, run_result: dict[str, Any]) -> dict[str, Any]:
    statuses = [s["status"] for s in data["steps"]]
    return {
        "report_id": data["report"]["report_id"],
        "run_id": data["report"]["run_id"],
        "case_id": data["report"]["case_id"],
        "case_name": data["report"]["case_name"],
        "status": run_result["overall_status"],
        "execution_date": data["report"]["execution_date"],
        "human_report_path": report_path,
        "step_count": len(statuses),
        "passed_steps": sum(1 for s in statuses if s == "passed"),
        "api_assertion_count": sum(1 for s in data["steps"] if s.get("api_assertion")),
        "ui_screenshot_count": sum(1 for s in data["steps"] if s.get("ui_evidence")),
        "evidence_score": data.get("score", {}).get("total")
        ,"canonical_run_result_ref": "run-result.json"
        ,"source_run_result_hash": run_result["run_result_hash"]
    }


def output_paths(data: dict[str, Any], root: Path) -> tuple[Path, Path]:
    grouping = data["grouping"]
    report = data["report"]
    rel = (
        Path(safe_segment(grouping["project_group_slug"], 12))
        / safe_segment(grouping["project_slug"], 12)
        / safe_segment(grouping["module_slug"], 14)
        / safe_segment(report["execution_date"], 10)
        / safe_segment(report["run_id"], 20)
    )
    return root / "human-html" / rel, root / "agent-readable" / rel


def safe_segment(value: str, max_len: int) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
    if len(cleaned) <= max_len:
        return cleaned
    digest = hashlib.sha1(cleaned.encode("utf-8")).hexdigest()[:10]
    return f"{cleaned[: max_len - 11]}-{digest}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    data = read_json(args.input)
    ensure_required(data)
    sensitive = scan_sensitive(data)
    if sensitive:
        raise ValueError("sensitive fields contain live values: " + ", ".join(sensitive))

    human_dir, agent_dir = output_paths(data, args.output_root)
    human_dir.mkdir(parents=True, exist_ok=True)
    agent_dir.mkdir(parents=True, exist_ok=True)
    report_path = human_dir / "report.html"
    report_rel = str(report_path)
    evidence_index = build_evidence_index(data, report_rel)
    run_result = build_canonical_run_result(data)
    data["report"]["status"] = run_result["overall_status"]
    execution_summary = build_execution_summary(data, report_rel, run_result)

    report_path.write_text(render_html(data), encoding="utf-8")
    (agent_dir / "evidence-index.json").write_text(json.dumps(evidence_index, ensure_ascii=False, indent=2), encoding="utf-8")
    (agent_dir / "run-result.json").write_text(json.dumps(run_result, ensure_ascii=False, indent=2), encoding="utf-8")
    (agent_dir / "execution-summary.json").write_text(json.dumps(execution_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": "generated",
        "report_html": str(report_path),
        "evidence_index": str(agent_dir / "evidence-index.json"),
        "execution_summary": str(agent_dir / "execution-summary.json")
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
