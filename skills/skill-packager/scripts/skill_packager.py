#!/usr/bin/env python3
import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path


SECRET_PATTERNS = [
    re.compile(r"(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_-])"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]+", re.I),
    re.compile(r"(password|token|cookie|apiKey|secret)\s*[:=]\s*['\"]?[^\s'\"]{8,}", re.I),
]


def now_iso():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path):
    return path.read_text(encoding="utf-8")


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_tree_clean(src, dst):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def parse_frontmatter(text):
    if not text.startswith("---"):
        raise ValueError("SKILL.md missing YAML frontmatter")
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", text, re.S)
    if not match:
        raise ValueError("Invalid frontmatter block")
    raw = match.group(1)
    body = match.group(2)
    data = {}
    current_key = None
    block_lines = []
    block_indent = None

    def flush_block():
        nonlocal current_key, block_lines, block_indent
        if current_key is not None:
            cleaned = []
            for line in block_lines:
                if block_indent is not None and line.startswith(" " * block_indent):
                    cleaned.append(line[block_indent:])
                else:
                    cleaned.append(line.strip())
            data[current_key] = " ".join(x.strip() for x in cleaned if x.strip()).strip()
        current_key = None
        block_lines = []
        block_indent = None

    for line in raw.splitlines():
        if current_key is not None:
            if re.match(r"^[A-Za-z0-9_-]+:\s*", line):
                flush_block()
            else:
                if line.strip():
                    indent = len(line) - len(line.lstrip(" "))
                    if block_indent is None:
                        block_indent = indent
                    block_lines.append(line)
                continue
        match_line = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not match_line:
            continue
        key, value = match_line.group(1), match_line.group(2).strip()
        if value in {">", ">-", "|", "|-"}:
            current_key = key
            block_lines = []
            block_indent = None
        else:
            data[key] = value.strip("\"'")
    flush_block()
    return data, raw, body


def render_frontmatter(data):
    lines = ["---"]
    for key, value in data.items():
        if key == "description":
            one_line = " ".join(str(value).split())
            lines.append(f"{key}: {one_line}")
        elif "\n" in str(value) or len(str(value)) > 110:
            lines.append(f"{key}: >-")
            words = str(value).split()
            line = []
            length = 0
            for word in words:
                if length + len(word) + 1 > 92:
                    lines.append("  " + " ".join(line))
                    line = [word]
                    length = len(word)
                else:
                    line.append(word)
                    length += len(word) + 1
            if line:
                lines.append("  " + " ".join(line))
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def validate_workbuddy_skill(skill_dir):
    skill_dir = Path(skill_dir)
    findings = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        findings.append({"severity": "P0", "message": "SKILL.md not found"})
        return findings
    try:
        fm, _, _ = parse_frontmatter(read_text(skill_md))
    except Exception as exc:
        return [{"severity": "P0", "message": f"frontmatter parse failed: {exc}"}]
    name = fm.get("name", "")
    description = fm.get("description", "")
    if not name:
        findings.append({"severity": "P0", "message": "missing name"})
    if not description:
        findings.append({"severity": "P0", "message": "missing description"})
    if name != skill_dir.name:
        findings.append({"severity": "P0", "message": f"name does not match directory: {name} != {skill_dir.name}"})
    if len(name) > 40:
        findings.append({"severity": "P0", "message": "name exceeds WorkBuddy 40-character limit"})
    if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", name):
        findings.append({"severity": "P0", "message": "name must be lowercase hyphen-case"})
    if "<" in description or ">" in description:
        findings.append({"severity": "P0", "message": "description must not contain angle brackets"})
    if fm.get("agent_created", "").lower() != "true":
        findings.append({"severity": "P0", "message": "agent_created: true is required for migrated user skills"})
    if (skill_dir / "agents").exists():
        findings.append({"severity": "P1", "message": "WorkBuddy runtime package should exclude agents/"})
    return findings


def scan_secrets(root):
    findings = []
    for path in Path(root).rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".yaml", ".yml", ".json", ".py", ".txt", ".html"}:
            continue
        try:
            text = read_text(path)
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            match = pattern.search(text)
            if match:
                findings.append({"severity": "P0", "path": str(path), "message": f"possible secret pattern: {match.group(0)[:32]}"})
                break
    return findings


def inventory(root):
    root = Path(root)
    items = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            items.append({
                "path": rel,
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            })
    return items


def make_workbuddy_package(source, dest):
    source = Path(source)
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for item in source.iterdir():
        if item.name == "agents":
            continue
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    skill_md = dest / "SKILL.md"
    fm, raw, body = parse_frontmatter(read_text(source / "SKILL.md"))
    name = fm.get("name", source.name)
    description = fm.get("description", "").replace("<", "[").replace(">", "]").strip()
    new_fm = {
        "name": name,
        "description": description,
        "agent_created": True,
    }
    write_text(skill_md, render_frontmatter(new_fm) + body)


def make_adapter_notes(source, output_root, source_inventory):
    source = Path(source)
    agents_yaml = source / "agents" / "openai.yaml"
    agents_note = "No Codex agents/openai.yaml found."
    if agents_yaml.exists():
        agents_note = read_text(agents_yaml)
    text = f"""# Agent Adapters

## Codex

Use the source package as-is. Keep `agents/openai.yaml` if present.

## WorkBuddy

Install user-level skills under:

`C:\\Users\\lenovo\\.workbuddy\\skills\\`

This package generates a WorkBuddy runtime folder that excludes `agents/` and rewrites frontmatter to:

- `name`
- `description`
- `agent_created: true`

Observed but unverified WorkBuddy extension fields are preserved in this adapter note or manifest until user-level behavior tests confirm their semantics.

### Codex Agent Metadata

```yaml
{agents_note}
```

## Generic Agent

Use `SKILL.md` as a procedural prompt and load referenced files manually. If scripts cannot run, perform static review only.

## File Count

Source file count: {len(source_inventory)}
"""
    write_text(output_root / "AGENT_ADAPTERS.md", text)


def make_portability_doc(output_root, source, target):
    text = f"""# Portability

Source skill: `{source}`

Target runtime: `{target}`

## Install

For WorkBuddy user-level deployment:

1. Dry-run first.
2. Backup existing destination if present.
3. Copy the generated WorkBuddy runtime folder to `C:\\Users\\lenovo\\.workbuddy\\skills\\`.
4. Validate hashes and frontmatter.

## Known Limits

- WorkBuddy builtin frontmatter samples contain fields whose user-level semantics are not fully verified.
- `disable-model-invocation` is not automatically generated by this packager.
- Target skill scripts are not executed during packaging.
"""
    write_text(output_root / "PORTABILITY.md", text)


def zip_dir(src_dir, zip_path):
    src_dir = Path(src_dir)
    zip_path = Path(zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(src_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(src_dir.parent))
    return zip_path


def verify_zip(zip_path, expected_inventory, folder_name, extract_dir):
    extract_dir = Path(extract_dir)
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)
    root = extract_dir / folder_name
    actual = {item["path"]: item["sha256"] for item in inventory(root)}
    missing = []
    mismatch = []
    for item in expected_inventory:
        path = item["path"]
        if path not in actual:
            missing.append(path)
        elif actual[path] != item["sha256"]:
            mismatch.append(path)
    return {"missing": missing, "mismatch": mismatch, "extractRoot": str(root)}


def render_report(path, title, data):
    rows = []
    for key, value in data.items():
        rows.append(f"<tr><th>{html.escape(str(key))}</th><td><pre>{html.escape(json.dumps(value, ensure_ascii=False, indent=2))}</pre></td></tr>")
    text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: "Microsoft YaHei", Arial, sans-serif; margin: 0; background: #f6f8fb; color: #17202a; line-height: 1.7; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 32px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; }}
    th, td {{ border: 1px solid #d8e0ee; padding: 10px; vertical-align: top; text-align: left; }}
    th {{ background: #edf2f7; width: 220px; }}
    pre {{ white-space: pre-wrap; margin: 0; }}
  </style>
</head>
<body><main>
<h1>{html.escape(title)}</h1>
<table>{''.join(rows)}</table>
</main></body></html>
"""
    write_text(path, text)


def package(args):
    source = Path(args.source).resolve()
    out = Path(args.out).resolve()
    target = args.target
    skill_name = source.name
    work = out / "package-work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    source_findings = []
    if not (source / "SKILL.md").exists():
        source_findings.append({"severity": "P0", "message": "source SKILL.md missing"})
    source_findings.extend(scan_secrets(source))
    if any(f["severity"] == "P0" for f in source_findings):
        raise SystemExit(f"blocked by P0 findings: {source_findings}")

    codex_root = work / "codex" / skill_name
    copy_tree_clean(source, codex_root)
    workbuddy_root = work / "workbuddy" / skill_name
    make_workbuddy_package(source, workbuddy_root)

    source_inv = inventory(source)
    codex_inv = inventory(codex_root)
    workbuddy_inv = inventory(workbuddy_root)
    wb_findings = validate_workbuddy_skill(workbuddy_root)
    make_adapter_notes(source, work, source_inv)
    make_portability_doc(work, source, target)

    manifest = {
        "schemaVersion": "1.0",
        "generatedAt": now_iso(),
        "source": str(source),
        "skillName": skill_name,
        "target": target,
        "sourceInventory": source_inv,
        "codexInventory": codex_inv,
        "workbuddyInventory": workbuddy_inv,
        "workbuddyFindings": wb_findings,
        "excludedFromWorkBuddy": ["agents/"] if (source / "agents").exists() else [],
    }
    write_text(work / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    provenance = {
        "generatedAt": now_iso(),
        "builder": "skill-packager",
        "source": str(source),
        "sourceSkillSha256": sha256_file(source / "SKILL.md"),
    }
    write_text(work / "provenance.json", json.dumps(provenance, ensure_ascii=False, indent=2))

    dist = out / "dist"
    codex_zip = zip_dir(codex_root, dist / f"{skill_name}-codex.zip")
    workbuddy_zip = zip_dir(workbuddy_root, dist / f"{skill_name}-workbuddy.zip")
    bundle_zip = zip_dir(work, dist / f"{skill_name}-portable-bundle.zip")
    verify = {
        "codex": verify_zip(codex_zip, codex_inv, skill_name, out / "verify" / "codex"),
        "workbuddy": verify_zip(workbuddy_zip, workbuddy_inv, skill_name, out / "verify" / "workbuddy"),
    }
    report_data = {
        "source": str(source),
        "workRoot": str(work),
        "codexZip": str(codex_zip),
        "workbuddyZip": str(workbuddy_zip),
        "bundleZip": str(bundle_zip),
        "workbuddyFindings": wb_findings,
        "verify": verify,
        "dryRun": args.dry_run,
    }
    render_report(out / "validation-report.html", "skill-packager validation report", report_data)
    print(json.dumps(report_data, ensure_ascii=False, indent=2))


def deploy(args):
    package_dir = Path(args.package).resolve()
    dest_root = Path(args.dest).resolve()
    dest = dest_root / package_dir.name
    backup_root = Path(args.backup_dir).resolve()
    files = inventory(package_dir)
    result = {
        "package": str(package_dir),
        "dest": str(dest),
        "fileCount": len(files),
        "dryRun": args.dry_run,
        "backup": None,
        "status": "dry-run",
    }
    if args.dry_run:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    backup_root.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = backup_root / f"{dest.name}-{stamp}"
        shutil.copytree(dest, backup)
        result["backup"] = str(backup)
        shutil.rmtree(dest)
    dest_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(package_dir, dest)
    result["status"] = "deployed"
    result["deployedInventory"] = inventory(dest)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Package and migrate Agent Skills")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("package")
    p.add_argument("--source", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--target", default="workbuddy", choices=["workbuddy", "codex"])
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=package)
    d = sub.add_parser("deploy")
    d.add_argument("--package", required=True)
    d.add_argument("--dest", required=True)
    d.add_argument("--backup-dir", required=True)
    d.add_argument("--dry-run", action="store_true")
    d.set_defaults(func=deploy)
    v = sub.add_parser("validate-workbuddy")
    v.add_argument("--skill", required=True)
    v.set_defaults(func=lambda args: print(json.dumps(validate_workbuddy_skill(args.skill), ensure_ascii=False, indent=2)))
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
