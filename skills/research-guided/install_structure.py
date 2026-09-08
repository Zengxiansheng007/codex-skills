#!/usr/bin/env python3
"""Create directory structure and move flat files into proper locations."""
import os, shutil, sys
base = os.path.dirname(os.path.abspath(__file__))

dirs = ["agents","references","scripts","fixtures","reports","schemas",
        "change-records/categories","change-records/entries/2026/2026-08"]
for d in dirs:
    os.makedirs(os.path.join(base, d), exist_ok=True)
    print("created dir:", d)
moves = {
    "agents-openai.yaml": "agents/openai.yaml",
    "ref-change-record-traceability.md": "references/change-record-traceability.md",
    "ref-claude-adapter-contract.md": "references/claude-adapter-contract.md",
    "ref-severity-and-fallback-rules.md": "references/severity-and-fallback-rules.md",
    "ref-decision-gate-rules.md": "references/decision-gate-rules.md",
    "scripts-validate_research_skill.py": "scripts/validate_research_skill.py",
    "scripts-test_research_skill.py": "scripts/test_research_skill.py",
    "scripts-scan_sensitive.py": "scripts/scan_sensitive.py",
}
for src, dst in moves.items():
    sp = os.path.join(base, src)
    dp = os.path.join(base, dst)
    if os.path.exists(sp):
        shutil.move(sp, dp)
        print("moved:", src, "->", dst)
cr_moves = {
    "cr-index.md": "change-records/index.md",
    "cr-cat-core-skill-md.md": "change-records/categories/core-skill-md.md",
    "cr-cat-references-and-assets.md": "change-records/categories/references-and-assets.md",
    "cr-cat-scripts-and-validation.md": "change-records/categories/scripts-and-validation.md",
    "cr-cat-safety-and-governance.md": "change-records/categories/safety-and-governance.md",
    "cr-cat-downstream-and-handoff.md": "change-records/categories/downstream-and-handoff.md",
}
for src, dst in cr_moves.items():
    sp = os.path.join(base, src)
    dp = os.path.join(base, dst)
    if os.path.exists(sp):
        shutil.move(sp, dp)
        print("moved:", src, "->", dst)
es = os.path.join(base, "cr-entry-001.md")
ed = os.path.join(base, "change-records/entries/2026/2026-08/CR-20260809-001-claude-research-loop.md")
if os.path.exists(es):
    shutil.move(es, ed)
    print("moved: cr-entry -> CR-001")
for tmp in ["test.txt","make_dirs.ps1","make_dirs.py","setup.py","setup_dirs.bat","setup_dirs.ps1","create_dirs.ps1","create_dirs.vbs","dir_script.txt","setup.cmd","make_dir.js","mkdir.ps1","dirs.ps1","agents.tmp"]:
    tp = os.path.join(base, tmp)
    if os.path.exists(tp):
        os.remove(tp)
        print("removed:", tmp)
print("ALL_FILES_STRUCTURED")
