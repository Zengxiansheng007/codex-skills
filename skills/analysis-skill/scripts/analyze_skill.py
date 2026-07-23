#!/usr/bin/env python3
"""Read-only R0 analysis for local Agent Skill directories or ZIP archives."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import tempfile
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import yaml


MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100
SCRIPT_SUFFIXES = {".py", ".ps1", ".sh", ".bash", ".js", ".cjs", ".mjs", ".ts", ".cmd", ".bat"}
LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
RESOURCE_PATTERN = re.compile(r"(?<![\w.-])((?:scripts|references|assets)/[A-Za-z0-9_./-]+)")
URL_PATTERN = re.compile(r"https?://[^\s\"'<>`]+")
ENV_PATTERN = re.compile(
    r"(?:process\.env\.[A-Z_][A-Z0-9_]*|os\.environ(?:\[[^\]]+\]|\.get\([^)]*\))|\$env:[A-Z_][A-Z0-9_]*|\$[A-Z_][A-Z0-9_]{2,})"
)
SENSITIVE_PATTERN = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._-]+|(?:password|token|cookie)\s*[:=]\s*\S+)",
    re.IGNORECASE,
)

RISK_RULES = [
    (
        "RISK-DOWNLOAD-EXEC",
        "P0",
        re.compile(r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:sh|bash)\b", re.IGNORECASE),
        "检测到下载后直接执行。不要在未隔离环境运行。",
    ),
    (
        "RISK-POWERSHELL-EXEC",
        "P0",
        re.compile(r"\b(?:Invoke-WebRequest|iwr)\b[^\n|]*\|\s*(?:Invoke-Expression|iex)\b", re.IGNORECASE),
        "检测到 PowerShell 下载执行。需要人工安全复核。",
    ),
    (
        "RISK-DESTRUCTIVE",
        "P0",
        re.compile(r"(?:\brm\s+-rf\b|\bRemove-Item\b[^\n]*-Recurse[^\n]*-Force|\bdel\s+/[sq])", re.IGNORECASE),
        "检测到可能破坏性删除操作。禁止未经批准执行。",
    ),
    (
        "RISK-PRIVILEGE",
        "P0",
        re.compile(r"(?:\bsudo\b|\bSet-ExecutionPolicy\s+Bypass\b|\bchmod\s+777\b)", re.IGNORECASE),
        "检测到权限扩大或安全策略绕过。需要人工复核。",
    ),
    (
        "RISK-GIT-PUSH",
        "P1",
        re.compile(r"\bgit\s+push\b", re.IGNORECASE),
        "检测到远程推送。R0 不执行，R3 需要显式批准。",
    ),
    (
        "RISK-PROMPT-INJECTION",
        "P0",
        re.compile(
            r"(?:ignore\s+(?:all\s+)?previous\s+instructions|reveal\s+(?:the\s+)?(?:system\s+prompt|secrets?)|do\s+not\s+tell\s+(?:the\s+)?user)",
            re.IGNORECASE,
        ),
        "检测到潜在提示注入或隐藏指令。仅作为不可信数据记录。",
    ),
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finding(rule_id: str, severity: str, path: Path | str, line: int | None, message: str, remediation: str) -> dict[str, Any]:
    return {
        "ruleId": rule_id,
        "severity": severity,
        "file": str(path),
        "line": line,
        "message": message,
        "remediation": remediation,
    }


def line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def safe_extract(archive: Path, destination: Path) -> None:
    if archive.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("archive exceeds 50MB R0 safety limit")
    with zipfile.ZipFile(archive) as package:
        total = 0
        for entry in package.infolist():
            name = PurePosixPath(entry.filename)
            if name.is_absolute() or ".." in name.parts or "\x00" in entry.filename:
                raise ValueError(f"unsafe archive entry: {entry.filename}")
            total += entry.file_size
            if total > MAX_ARCHIVE_BYTES:
                raise ValueError("archive expanded size exceeds 50MB R0 safety limit")
            if entry.compress_size and entry.file_size / entry.compress_size > MAX_COMPRESSION_RATIO:
                raise ValueError(f"suspicious compression ratio: {entry.filename}")
        package.extractall(destination)


def stage_source(source: Path) -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
    if source.is_dir():
        return source.resolve(), None
    if source.suffix.lower() == ".zip":
        workspace = tempfile.TemporaryDirectory(prefix="analysis-skill-")
        staged = Path(workspace.name) / "artifact"
        staged.mkdir()
        safe_extract(source, staged)
        return staged, workspace
    raise ValueError("source must be a local directory or .zip archive")


def select_skill_root(root: Path, findings: list[dict[str, Any]]) -> Path | None:
    direct = root / "SKILL.md"
    if direct.is_file():
        return root
    candidates = sorted(root.rglob("SKILL.md"))
    if len(candidates) == 1:
        return candidates[0].parent
    if not candidates:
        findings.append(finding("STRUCTURE-SKILL-MISSING", "P0", root, None, "未找到 SKILL.md。", "提供完整 Skill 包或指定正确目录。"))
    else:
        findings.append(finding("STRUCTURE-MULTIPLE-SKILLS", "P1", root, None, "发现多个 SKILL.md，当前输入不是单一 Skill artifact。", "拆分分析目标或在上层指定目标 Skill。"))
    return None


def parse_frontmatter(skill_file: Path, findings: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    text = skill_file.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        findings.append(finding("FRONTMATTER-MISSING", "P0", skill_file, 1, "SKILL.md 缺少 YAML frontmatter。", "在文件开头添加 name 和 description。"))
        return None, text
    closing = next((index for index, value in enumerate(lines[1:], 1) if value.strip() == "---"), None)
    if closing is None:
        findings.append(finding("FRONTMATTER-UNCLOSED", "P0", skill_file, 1, "YAML frontmatter 未闭合。", "补充 closing ---。"))
        return None, text
    raw = "\n".join(lines[1:closing])
    try:
        parsed = yaml.safe_load(raw) or {}
    except yaml.YAMLError as error:
        findings.append(finding("FRONTMATTER-INVALID", "P0", skill_file, 1, f"YAML 解析失败：{error}", "修复 YAML 语法后重跑。"))
        return None, text
    if not isinstance(parsed, dict):
        findings.append(finding("FRONTMATTER-NONOBJECT", "P0", skill_file, 1, "YAML frontmatter 必须是对象。", "使用 name/description 键值结构。"))
        return None, text
    name = parsed.get("name")
    description = parsed.get("description")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        findings.append(finding("FRONTMATTER-NAME", "P1", skill_file, 1, "name 缺失或不符合小写连字符格式。", "使用与目录匹配的小写连字符名称。"))
    if not isinstance(description, str) or not description.strip():
        findings.append(finding("FRONTMATTER-DESCRIPTION", "P1", skill_file, 1, "description 缺失或为空。", "描述能力及具体触发场景。"))
    return parsed, text


def scan_text(path: Path, text: str, findings: list[dict[str, Any]]) -> None:
    for rule_id, severity, pattern, remediation in RISK_RULES:
        for match in pattern.finditer(text):
            findings.append(finding(rule_id, severity, path, line_of(text, match.start()), f"命中规则 {rule_id}。", remediation))
    for match in SENSITIVE_PATTERN.finditer(text):
        findings.append(
            finding(
                "RISK-SENSITIVE-PATTERN",
                "P0",
                path,
                line_of(text, match.start()),
                "发现疑似凭据或敏感赋值模式。",
                "移除凭据，改用运行时安全注入，并对历史泄露进行轮换。",
            )
        )


def section_text(markdown: str, heading_keywords: list[str]) -> str:
    lines = markdown.splitlines()
    capture = False
    captured: list[str] = []
    for line in lines:
        if line.lstrip().startswith("#"):
            heading = line.strip("# ").lower()
            if capture:
                break
            capture = any(keyword.lower() in heading for keyword in heading_keywords)
            continue
        if capture:
            captured.append(line)
    return "\n".join(captured).strip()


def markdown_headings(markdown: str) -> list[dict[str, Any]]:
    headings = []
    for index, line in enumerate(markdown.splitlines(), 1):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            headings.append({"level": len(match.group(1)), "title": match.group(2), "line": index})
    return headings


def bullet_lines(text: str, limit: int = 12) -> list[str]:
    values = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^(?:[-*]|\d+\.)\s+", stripped):
            values.append(re.sub(r"^(?:[-*]|\d+\.)\s+", "", stripped))
    return values[:limit]


def code_commands(text: str) -> list[str]:
    commands = []
    in_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_block = not in_block
            continue
        if in_block and stripped:
            commands.append(stripped)
    return commands


def resolve_purpose(requested: str, skill_text: str) -> str:
    if requested != "auto":
        return requested
    text = skill_text.lower()
    redesign_terms = ["redesign", "refactor", "重设计", "重构", "改造", "运行逻辑", "设计分析"]
    adoption_terms = ["adopt", "install", "execute", "audit", "security", "采用", "安装", "执行", "审计", "安全"]
    redesign = any(term in text for term in redesign_terms)
    adoption = any(term in text for term in adoption_terms)
    if redesign and not adoption:
        return "redesign"
    if adoption and not redesign:
        return "adoption"
    return "adoption-and-redesign"


def classify_resource(path: str, referenced: bool) -> dict[str, Any]:
    if path.startswith("scripts/"):
        role = "deterministic helper or validator"
        load_phase = "execution or validation gate"
    elif path.startswith("references/"):
        role = "progressive-disclosure guidance"
        load_phase = "read when the matching workflow branch is selected"
    elif path.startswith("assets/"):
        role = "fixture, template, or reusable asset"
        load_phase = "test or artifact generation"
    else:
        role = "package file"
        load_phase = "inventory"
    return {
        "path": path,
        "role": role,
        "referencedFromSkillMd": referenced,
        "loadPhase": load_phase,
        "isOrphanCandidate": path.startswith(("scripts/", "references/")) and not referenced,
        "scriptizeCandidate": path.startswith("references/") and "checklist" in path.lower(),
    }


def build_evidence(report: dict[str, Any], skill_text: str, referenced_resources: set[str]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    selected = report["artifact"].get("skillFile")
    if selected:
        evidence.append(
            {
                "id": "E-SKILL-001",
                "sourcePath": selected,
                "location": "SKILL.md",
                "quoteOrSummary": "Skill entrypoint and primary operating instructions parsed as untrusted local content.",
                "trustLevel": "untrusted-local-content",
                "extractionMethod": "frontmatter and markdown parse",
            }
        )
    if report.get("frontmatter"):
        evidence.append(
            {
                "id": "E-FRONTMATTER-001",
                "sourcePath": selected,
                "location": "YAML frontmatter",
                "quoteOrSummary": "name and description extracted from SKILL.md frontmatter.",
                "trustLevel": "declared-metadata",
                "extractionMethod": "yaml.safe_load",
            }
        )
    for index, resource in enumerate(sorted(referenced_resources), 1):
        evidence.append(
            {
                "id": f"E-RESOURCE-{index:03d}",
                "sourcePath": resource,
                "location": "SKILL.md resource reference",
                "quoteOrSummary": "Resource path referenced by SKILL.md.",
                "trustLevel": "declared-reference",
                "extractionMethod": "regex resource extraction",
            }
        )
    for index, item in enumerate(report["findings"], 1):
        evidence_id = f"E-FINDING-{index:03d}"
        item["evidenceIds"] = [evidence_id]
        evidence.append(
            {
                "id": evidence_id,
                "sourcePath": item["file"],
                "location": f"line {item['line']}" if item.get("line") else "file-level",
                "quoteOrSummary": f"{item['ruleId']} / {item['severity']}: {item['message']}",
                "trustLevel": "static-rule-result",
                "extractionMethod": "deterministic scanner",
            }
        )
    return evidence


def design_analysis(frontmatter: dict[str, Any] | None, skill_text: str, findings: list[dict[str, Any]]) -> dict[str, Any]:
    description = str((frontmatter or {}).get("description") or "").strip()
    workflow = section_text(skill_text, ["workflow"])
    validation = section_text(skill_text, ["validation"])
    headings = markdown_headings(skill_text)
    target_users = []
    lower = skill_text.lower()
    for label, terms in {
        "Codex agent": ["codex", "agent"],
        "skill designer": ["skill", "设计", "创建", "改造"],
        "security reviewer": ["security", "安全", "audit", "review"],
        "test executor": ["test", "测试", "validation"],
    }.items():
        if any(term in lower for term in terms):
            target_users.append(label)
    design_gaps = []
    if not validation:
        design_gaps.append({"id": "DG-VALIDATION-MISSING", "type": "validation", "message": "未发现明确 Validation 章节。", "confidence": "high"})
    if len(skill_text.splitlines()) > 500:
        design_gaps.append({"id": "DG-SKILLMD-LONG", "type": "context", "message": "SKILL.md 超过 500 行，建议拆分引用。", "confidence": "high"})
    for item in findings:
        if item["severity"] in {"P1", "P2"}:
            design_gaps.append(
                {
                    "id": f"DG-{item['ruleId']}",
                    "type": "finding-derived",
                    "message": item["message"],
                    "confidence": "high",
                    "evidenceIds": item.get("evidenceIds", []),
                }
            )
    success_criteria = bullet_lines(validation) or code_commands(validation)
    strengths = []
    if description:
        strengths.append("frontmatter description declares capability and trigger surface")
    if workflow:
        strengths.append("workflow section gives an ordered operating path")
    if validation:
        strengths.append("validation section defines post-change checks")
    return {
        "problemSolved": description or "unknown",
        "targetUsers": target_users or ["unknown"],
        "triggerScenarios": [description] if description else [],
        "skillType": "operational-playbook-with-static-analysis" if "analyze" in lower or "分析" in skill_text else "operational-playbook",
        "successCriteria": success_criteria,
        "headings": headings,
        "strengthsToKeep": strengths,
        "designGaps": design_gaps,
        "confidence": "medium" if description else "low",
    }


def runtime_model(skill_text: str, scripts: list[str], referenced_resources: set[str]) -> dict[str, Any]:
    workflow = section_text(skill_text, ["workflow"])
    decision_rules = section_text(skill_text, ["decision"])
    validation = section_text(skill_text, ["validation"])
    workflow_items = bullet_lines(workflow)
    stages = [
        {
            "id": f"STAGE-{index:02d}",
            "name": item[:90],
            "inputs": ["parsedSkill", "artifactManifest"] if index > 1 else ["source artifact", "user request"],
            "actions": [item],
            "outputs": ["intermediate analysis state"],
            "decisionPoints": [],
            "handoffTargets": [],
        }
        for index, item in enumerate(workflow_items, 1)
    ]
    if not stages:
        stages = [
            {"id": "STAGE-01", "name": "Collect and parse Skill artifact", "inputs": ["source artifact"], "actions": ["Read SKILL.md and package resources"], "outputs": ["parsedSkill"], "decisionPoints": [], "handoffTargets": []},
            {"id": "STAGE-02", "name": "Analyze and report", "inputs": ["parsedSkill"], "actions": ["Run static checks and synthesize findings"], "outputs": ["HTML report", "JSON evidence"], "decisionPoints": [], "handoffTargets": []},
        ]
    commands = code_commands(validation)
    outputs = []
    if re.search(r"\bHTML\b|html", skill_text):
        outputs.append("HTML report")
    if re.search(r"\bJSON\b|json", skill_text):
        outputs.append("JSON evidence index")
    if not outputs:
        outputs.append("human-readable recommendation")
    return {
        "inputs": ["local Skill directory", "ZIP archive", "staged GitHub snapshot", "target profile", "analysis purpose"],
        "workflowStages": stages,
        "decisionPoints": bullet_lines(decision_rules)[:12],
        "scripts": [{"path": path, "status": "unverified-r0", "role": "declared executable helper"} for path in scripts],
        "referencesUsed": sorted(resource for resource in referenced_resources if resource.startswith("references/")),
        "outputs": outputs,
        "validationLoop": commands,
    }


def logic_design(security: dict[str, Any], design: dict[str, Any], runtime: dict[str, Any], resource_roles: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "modules": [
            {"name": "SourceNormalizer", "responsibility": "stage local or ZIP sources safely and enumerate files", "inputs": ["source"], "outputs": ["artifactManifest"]},
            {"name": "SkillParser", "responsibility": "parse SKILL.md, frontmatter, headings, links, and resource references", "inputs": ["artifactManifest"], "outputs": ["parsedSkill"]},
            {"name": "SecurityAnalyzer", "responsibility": "run deterministic R0 risk and compatibility checks", "inputs": ["parsedSkill", "files"], "outputs": ["securityAnalysis"]},
            {"name": "DesignAnalyzer", "responsibility": "infer problem, users, triggers, strengths, and design gaps", "inputs": ["parsedSkill"], "outputs": ["designAnalysis"]},
            {"name": "RuntimeModelBuilder", "responsibility": "extract workflow stages, decision points, scripts, references, outputs, and validation loop", "inputs": ["parsedSkill"], "outputs": ["runtimeModel"]},
            {"name": "LogicSynthesizer", "responsibility": "join evidence, confidence rules, module boundaries, and redesign implications", "inputs": ["securityAnalysis", "designAnalysis", "runtimeModel"], "outputs": ["logicDesign"]},
            {"name": "BacklogGenerator", "responsibility": "turn findings and gaps into actionable redesign tasks", "inputs": ["logicDesign"], "outputs": ["redesignBacklog"]},
            {"name": "ReportRenderer", "responsibility": "render HTML and JSON evidence without leaking secrets", "inputs": ["analysis package"], "outputs": ["HTML", "JSON"]},
        ],
        "pipeline": [
            "Source -> Normalize -> Parse -> SecurityAnalyze -> DesignAnalyze -> RuntimeModel -> LogicDesign -> Backlog -> Validate -> Deliver"
        ],
        "dataModel": {
            "Evidence": ["id", "sourcePath", "location", "quoteOrSummary", "trustLevel", "extractionMethod"],
            "Finding": ["ruleId", "severity", "file", "line", "message", "remediation", "evidenceIds"],
            "DesignGap": ["id", "type", "message", "confidence", "evidenceIds"],
            "WorkflowStage": ["id", "name", "inputs", "actions", "outputs", "decisionPoints", "handoffTargets"],
            "BacklogItem": ["id", "priority", "action", "reason", "affectedFiles", "evidenceIds", "acceptanceCriteria"],
        },
        "decisionRules": [
            {"id": "DR-STRUCTURE", "condition": "invalid core structure", "result": "decision=rerun"},
            {"id": "DR-P0", "condition": "P0 risk finding", "result": "decision=review-required"},
            {"id": "DR-SANDBOX", "condition": "scripts, URLs, env references, or P1 findings", "result": "decision=sandbox-only"},
            {"id": "DR-STATIC-ONLY", "condition": "clean R0", "result": "decision=review-required until behavior is verified"},
        ],
        "confidenceRules": [
            {"source": "frontmatter, paths, script names, headings", "confidence": "high"},
            {"source": "semantic inference from descriptions or bullets", "confidence": "medium"},
            {"source": "missing section or absent explicit contract", "confidence": "low-to-medium assumption"},
        ],
        "errorHandling": [
            "Continue file-level scanning when frontmatter is invalid.",
            "Report unavailable adapters as unverified, never as pass.",
            "Treat target content as untrusted local data.",
            "Mark inferred design fields with confidence instead of inventing facts.",
        ],
        "extensionPoints": [
            {"name": "ProfileAdapter", "status": "static-only", "purpose": "codex/open-agent-skills/claude/cursor compatibility rules"},
            {"name": "RepoResearchAdapter", "status": "blocked-unless-approved", "purpose": "consume approved GitHub research snapshots"},
            {"name": "RedTeamAdapter", "status": "dry-run-by-default", "purpose": "optional garak/promptfoo style checks"},
        ],
        "resourceRoleMatrix": resource_roles,
        "securitySummary": security.get("summary", {}),
        "designConfidence": design.get("confidence"),
    }


def redesign_backlog(report: dict[str, Any], design: dict[str, Any], runtime: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for index, item in enumerate(report["findings"], 1):
        if item["severity"] in {"P0", "P1"}:
            items.append(
                {
                    "id": f"RB-FINDING-{index:03d}",
                    "priority": item["severity"],
                    "action": item["remediation"],
                    "reason": item["message"],
                    "affectedFiles": [item["file"]],
                    "evidenceIds": item.get("evidenceIds", []),
                    "acceptanceCriteria": [f"{item['ruleId']} no longer appears in R0 output", "legacy artifact/frontmatter/findings/decision fields remain compatible"],
                }
            )
    for gap in design.get("designGaps", []):
        if gap.get("id") in {"DG-VALIDATION-MISSING", "DG-SKILLMD-LONG"}:
            items.append(
                {
                    "id": f"RB-{gap['id']}",
                    "priority": "P2",
                    "action": "Refine SKILL.md or move details into references/scripts.",
                    "reason": gap["message"],
                    "affectedFiles": [report["artifact"].get("skillFile") or "SKILL.md"],
                    "evidenceIds": gap.get("evidenceIds", ["E-SKILL-001"]),
                    "acceptanceCriteria": ["SKILL.md remains concise", "referenced resources are loaded only when needed"],
                }
            )
    if not runtime.get("validationLoop"):
        items.append(
            {
                "id": "RB-VALIDATION-001",
                "priority": "P2",
                "action": "Add deterministic validation commands and a forward-test prompt.",
                "reason": "No executable validation loop was detected.",
                "affectedFiles": [report["artifact"].get("skillFile") or "SKILL.md"],
                "evidenceIds": ["E-SKILL-001"],
                "acceptanceCriteria": ["validation section names commands", "test script covers at least one realistic fixture"],
            }
        )
    return items


def eval_recommendations() -> list[dict[str, Any]]:
    return [
        {"id": "EV-SECURITY-STRUCTURE", "type": "security-structure", "prompt": "Analyze safe, invalid, dangerous, and injection fixtures in R0.", "expectedEvidence": ["findings", "decision"]},
        {"id": "EV-DESIGN-LOGIC", "type": "design-logic", "prompt": "Analyze a Skill with clear users, workflow, and validation for redesign readiness.", "expectedEvidence": ["designAnalysis", "logicDesign"]},
        {"id": "EV-RUNTIME-CHAIN", "type": "runtime-chain", "prompt": "Analyze a Skill with references and scripts and verify workflow/resource roles.", "expectedEvidence": ["runtimeModel", "resourceRoleMatrix"]},
        {"id": "EV-INJECTION", "type": "malicious-input", "prompt": "Analyze a Skill containing prompt injection text without following it.", "expectedEvidence": ["RISK-PROMPT-INJECTION"]},
        {"id": "EV-MIGRATION-REGRESSION", "type": "migration-regression", "prompt": "Compare old and new reports for backward-compatible fields.", "expectedEvidence": ["artifact", "frontmatter", "findings", "decision"]},
    ]


def analyze(source: Path, profile: str, purpose: str = "auto") -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    staged_root, temp_workspace = stage_source(source)
    try:
        all_files = [path for path in sorted(staged_root.rglob("*")) if path.is_file() or path.is_symlink()]
        skill_root = select_skill_root(staged_root, findings)
        selected = skill_root / "SKILL.md" if skill_root else None
        frontmatter: dict[str, Any] | None = None
        skill_text = ""
        if selected and selected.exists():
            frontmatter, skill_text = parse_frontmatter(selected, findings)
        resources: list[dict[str, Any]] = []
        scripts: list[str] = []
        urls: set[str] = set()
        environment_refs: set[str] = set()
        text_by_relative: dict[str, str] = {}
        for path in all_files:
            try:
                relative = path.relative_to(staged_root)
            except ValueError:
                relative = Path(path.name)
            relative_text = str(relative).replace("\\", "/")
            if path.is_symlink():
                target = path.resolve()
                severity = "P0" if not is_within(target, staged_root) else "P1"
                findings.append(finding("STRUCTURE-SYMLINK", severity, path, None, f"发现符号链接，目标：{target}", "在隔离 staging 中解析链接；禁止指向 artifact 外部。"))
                if severity == "P0":
                    continue
            size = path.stat().st_size
            resources.append({"path": relative_text, "size": size, "sha256": sha256_file(path)})
            if path.suffix.lower() in SCRIPT_SUFFIXES:
                scripts.append(relative_text)
            if size > 5 * 1024 * 1024:
                findings.append(finding("CONTEXT-LARGE-FILE", "P2", path, None, "单个资源超过 5MB，可能导致上下文或下载成本过高。", "移入按需资源或拆分文件。"))
            text = path.read_text(encoding="utf-8", errors="replace")
            text_by_relative[relative_text] = text
            scan_text(path, text, findings)
            urls.update(URL_PATTERN.findall(text))
            environment_refs.update(ENV_PATTERN.findall(text))
        referenced_resources: set[str] = set()
        if selected and skill_root:
            for match in LINK_PATTERN.finditer(skill_text):
                target = match.group(1).strip().split("#", 1)[0]
                if not target or re.match(r"(?:https?://|mailto:)", target):
                    continue
                referenced_resources.add(target.replace("\\", "/"))
                resolved = (skill_root / target).resolve()
                if not is_within(resolved, skill_root):
                    findings.append(finding("LINK-ESCAPES-SKILL", "P1", selected, line_of(skill_text, match.start()), f"相对引用越出 Skill 目录：{target}", "改为包内相对引用。"))
                elif not resolved.exists():
                    findings.append(finding("LINK-MISSING", "P1", selected, line_of(skill_text, match.start()), f"内部引用不存在：{target}", "修复或删除引用。"))
            for match in RESOURCE_PATTERN.finditer(skill_text):
                target = match.group(1).strip().replace("\\", "/")
                referenced_resources.add(target)
                if not (skill_root / target).exists():
                    findings.append(finding("RESOURCE-MISSING", "P1", selected, line_of(skill_text, match.start()), f"资源引用不存在：{target}", "补充资源或修正路径。"))
            if skill_text.count("```") % 2:
                findings.append(finding("MARKDOWN-FENCE", "P1", selected, None, "Markdown code fence 数量不成对。", "闭合未结束的代码块。"))
        if urls:
            findings.append(finding("CAPABILITY-NETWORK", "P1", selected or staged_root, None, f"发现 {len(urls)} 个外部 URL。", "R3 前确认网络 allowlist 与数据外发范围。"))
        if scripts:
            findings.append(finding("CAPABILITY-SCRIPTS", "P1", selected or staged_root, None, f"发现 {len(scripts)} 个可执行脚本。", "R0 不执行；R3 前审查脚本和最小权限。"))
        if environment_refs:
            findings.append(finding("CAPABILITY-ENV", "P1", selected or staged_root, None, f"发现 {len(environment_refs)} 个环境变量引用。", "确认变量用途，禁止在报告中记录真实值。"))
        counts = Counter(item["severity"] for item in findings)
        structural_error = any(item["ruleId"].startswith(("FRONTMATTER-", "STRUCTURE-SKILL-")) for item in findings)
        security_p0 = any(item["severity"] == "P0" and item["ruleId"].startswith("RISK-") for item in findings)
        artifact_digest = hashlib.sha256(
            "\n".join(f"{item['path']}:{item['sha256']}" for item in resources).encode("utf-8")
        ).hexdigest()
        if structural_error and not security_p0:
            decision = "rerun"
        elif not selected or security_p0:
            decision = "review-required"
        elif counts["P1"] or scripts or urls:
            decision = "sandbox-only"
        else:
            decision = "review-required"
        report: dict[str, Any] = {
            "metadata": {
                "tool": "analysis-skill",
                "mode": "R0",
                "profile": profile,
                "generatedAt": datetime.now(timezone.utc).isoformat(),
            },
            "analysisPurpose": resolve_purpose(purpose, skill_text),
            "artifact": {
                "source": str(source.resolve()),
                "stagedRoot": str(staged_root),
                "skillRoot": str(skill_root) if skill_root else None,
                "skillFile": str(selected) if selected else None,
                "artifactHash": artifact_digest,
                "fileCount": len(resources),
                "files": resources,
            },
            "frontmatter": frontmatter,
            "capabilities": {"scripts": scripts, "externalUrls": sorted(urls), "environmentReferences": sorted(environment_refs)},
            "findings": findings,
            "summary": {"P0": counts["P0"], "P1": counts["P1"], "P2": counts["P2"], "staticStatus": "complete"},
            "decision": {
                "status": decision,
                "reason": "R0 static analysis only; behavior and runtime compatibility remain unverified.",
                "nextStep": "Request explicit approval before dependency installation, external review, or R3 sandbox execution.",
            },
        }
        report["evidenceIndex"] = build_evidence(report, skill_text, referenced_resources)
        report["securityAnalysis"] = {
            "artifact": report["artifact"],
            "frontmatter": report["frontmatter"],
            "capabilities": report["capabilities"],
            "findings": report["findings"],
            "decision": report["decision"],
        }
        report["designAnalysis"] = design_analysis(frontmatter, skill_text, findings)
        report["runtimeModel"] = runtime_model(skill_text, scripts, referenced_resources)
        report["resourceRoleMatrix"] = [
            classify_resource(item["path"], item["path"] in referenced_resources)
            for item in resources
            if item["path"].startswith(("references/", "scripts/", "assets/"))
        ]
        report["logicDesign"] = logic_design(report, report["designAnalysis"], report["runtimeModel"], report["resourceRoleMatrix"])
        report["redesignBacklog"] = redesign_backlog(report, report["designAnalysis"], report["runtimeModel"])
        report["evalRecommendations"] = eval_recommendations()
        report["openQuestions"] = [
            "Which platform profile should be treated as the primary redesign target?",
            "Should inferred design gaps be converted directly into implementation tasks?",
        ]
        return report
    finally:
        if temp_workspace is not None:
            temp_workspace.cleanup()


def html_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return f"<tr><td colspan=\"{len(columns)}\">无。</td></tr>"
    rendered = []
    for row in rows:
        cells = []
        for key, _label in columns:
            value = row.get(key, "")
            if isinstance(value, (list, dict)):
                value = json.dumps(value, ensure_ascii=False)
            cells.append(f"<td>{html.escape(str(value if value is not None else ''))}</td>")
        rendered.append("<tr>" + "".join(cells) + "</tr>")
    return "".join(rendered)


def html_report(report: dict[str, Any]) -> str:
    def cell(value: Any) -> str:
        return html.escape(str(value if value is not None else ""))

    findings = html_table(
        report["findings"],
        [("severity", "级别"), ("ruleId", "规则"), ("file", "文件"), ("line", "行"), ("message", "信息"), ("remediation", "修复"), ("evidenceIds", "证据")],
    )
    resources = html_table(report["artifact"]["files"], [("path", "路径"), ("size", "大小"), ("sha256", "SHA-256")])
    backlog = html_table(
        report["redesignBacklog"],
        [("priority", "优先级"), ("id", "ID"), ("action", "动作"), ("reason", "原因"), ("affectedFiles", "影响文件"), ("evidenceIds", "证据")],
    )
    resource_roles = html_table(
        report["resourceRoleMatrix"],
        [("path", "路径"), ("role", "职责"), ("referencedFromSkillMd", "被入口引用"), ("loadPhase", "加载阶段"), ("isOrphanCandidate", "孤立候选")],
    )
    evals = html_table(report["evalRecommendations"], [("id", "ID"), ("type", "类型"), ("prompt", "测试提示"), ("expectedEvidence", "证据")])
    embedded = json.dumps(report, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>Skill 分析报告</title>
<style>body{{font-family:"Microsoft YaHei",Arial,sans-serif;line-height:1.6;color:#17202a;margin:0;background:#f5f7fa}}main{{max-width:1180px;margin:24px auto;padding:32px;background:#fff;border:1px solid #d8e0e7}}h2{{margin-top:30px;border-bottom:2px solid #d8e0e7;padding-bottom:6px}}table{{width:100%;border-collapse:collapse;margin:12px 0}}th,td{{border:1px solid #d8e0e7;padding:8px;vertical-align:top;text-align:left}}th{{background:#edf2f6}}.summary{{padding:14px;background:#eaf2fa;border-left:4px solid #1f5f99}}code{{word-break:break-all}}pre{{white-space:pre-wrap;background:#f3f6f9;padding:12px;border:1px solid #d8e0e7;overflow:auto}}</style></head>
<body><main><h1>Skill 静态与重设计分析报告</h1>
<section class="summary"><strong>R0 结论：{cell(report['decision']['status'])}</strong><br>{cell(report['decision']['reason'])}<br><strong>分析目的：</strong>{cell(report['analysisPurpose'])}</section>
<h2>Artifact 身份</h2><table><tr><th>来源</th><td>{cell(report['artifact']['source'])}</td></tr><tr><th>Skill 文件</th><td>{cell(report['artifact']['skillFile'])}</td></tr><tr><th>Artifact SHA-256</th><td><code>{cell(report['artifact']['artifactHash'])}</code></td></tr><tr><th>目标 profile</th><td>{cell(report['metadata']['profile'])}</td></tr><tr><th>文件数</th><td>{cell(report['artifact']['fileCount'])}</td></tr></table>
<h2>Frontmatter</h2><pre>{cell(json.dumps(report['frontmatter'], ensure_ascii=False, indent=2))}</pre>
<h2>声明能力</h2><pre>{cell(json.dumps(report['capabilities'], ensure_ascii=False, indent=2))}</pre>
<h2>安全 Findings</h2><table><thead><tr><th>级别</th><th>规则</th><th>文件</th><th>行</th><th>信息</th><th>修复</th><th>证据</th></tr></thead><tbody>{findings}</tbody></table>
<h2>设计分析</h2><pre>{cell(json.dumps(report['designAnalysis'], ensure_ascii=False, indent=2))}</pre>
<h2>运行模型</h2><pre>{cell(json.dumps(report['runtimeModel'], ensure_ascii=False, indent=2))}</pre>
<h2>逻辑设计</h2><pre>{cell(json.dumps(report['logicDesign'], ensure_ascii=False, indent=2))}</pre>
<h2>资源职责矩阵</h2><table><thead><tr><th>路径</th><th>职责</th><th>被入口引用</th><th>加载阶段</th><th>孤立候选</th></tr></thead><tbody>{resource_roles}</tbody></table>
<h2>重构 Backlog</h2><table><thead><tr><th>优先级</th><th>ID</th><th>动作</th><th>原因</th><th>影响文件</th><th>证据</th></tr></thead><tbody>{backlog}</tbody></table>
<h2>Eval 建议</h2><table><thead><tr><th>ID</th><th>类型</th><th>测试提示</th><th>证据</th></tr></thead><tbody>{evals}</tbody></table>
<h2>文件清单</h2><table><thead><tr><th>路径</th><th>大小</th><th>SHA-256</th></tr></thead><tbody>{resources}</tbody></table>
<h2>下一步</h2><p>{cell(report['decision']['nextStep'])}</p></main><script type="application/json" id="analysis-evidence">{embedded}</script></body></html>"""


def write_report(report: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html_report(report), encoding="utf-8")
    output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only R0 Agent Skill analyzer")
    parser.add_argument("source", type=Path, help="local Skill directory or ZIP archive")
    parser.add_argument("--output", type=Path, required=True, help="HTML output path outside the source artifact")
    parser.add_argument("--profile", choices=["codex", "open-agent-skills", "claude", "cursor"], default="codex")
    parser.add_argument("--purpose", choices=["auto", "adoption", "redesign", "adoption-and-redesign"], default="auto")
    parser.add_argument("--fail-on-p0", action="store_true", help="return 2 when P0 findings are detected")
    args = parser.parse_args(argv)
    try:
        if args.source.is_dir() and is_within(args.output, args.source):
            raise ValueError("output must be outside the source artifact to preserve read-only analysis")
        report = analyze(args.source, args.profile, args.purpose)
        write_report(report, args.output)
        print(f"report: {args.output}")
        print(f"decision: {report['decision']['status']}")
        return 2 if args.fail_on_p0 and report["summary"]["P0"] else 0
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"analysis failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
