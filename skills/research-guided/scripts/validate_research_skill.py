#!/usr/bin/env python3
"""Validate a research Skill package."""
from __future__ import annotations
import argparse, json, re, sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import yaml
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
SECRET_RE = re.compile(r"sk-[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._-]+|(?i:password|token|cookie)\s*[:=]\s*\S+")
DANGEROUS_RE = re.compile(r"(?:\brm\s+-rf|Remove-Item\b[^\n]*-Recurse[^\n]*-Force|curl\b[^\n|]*\|\s*(?:sh|bash))", re.IGNORECASE)
RESOURCE_RE = re.compile(r"(?<![\w.-])((?:references|scripts|fixtures)/[A-Za-z0-9_./ -]+\.[A-Za-z0-9]+)")
CHANGE_ID_RE = re.compile(r"CR-\d{8}-\d{3}")
ENTRY_SECTIONS = ["## Summary","## Context And Problem","## Sections Changed","## Decision And Alternatives","## Impact Analysis","## Validation Evidence","## Safety And Privacy","## Risks And Follow-up"]

@dataclass
class Finding:
    severity: str; rule: str; file: str; message: str; fix: str
def add(f,s,r,f2,m,x): f.append(Finding(s,r,str(f2),m,x))
def parse_fm(sf,fd):
    t=sf.read_text(encoding="utf-8",errors="replace")
    if not t.startswith("---\n"): add(fd,"P0","fm-missing",sf,"No frontmatter.","Add it.");return None,t
    e=t.find("\n---\n",4)
    if e==-1: add(fd,"P0","fm-unclosed",sf,"Not closed.","Close it.");return None,t
    try: d=yaml.safe_load(t[4:e]) or {}
    except Exception as ex: add(fd,"P0","fm-invalid",sf,f"YAML error: {ex}","Fix.");return None,t
    if not isinstance(d,dict): add(fd,"P0","fm-object",sf,"Must be mapping.","Fix.");return None,t
    return d,t
def validate(root):
    fd=[]; sf=root/"SKILL.md"
    if not root.exists(): add(fd,"P0","root-missing",root,"Missing.","Provide.");return result(root,None,fd)
    if not sf.exists(): add(fd,"P0","md-missing",sf,"Missing.","Create.");return result(root,None,fd)
    fm,t=parse_fm(sf,fd)
    if fm:
        n=fm.get("name")
        if not isinstance(n,str) or not NAME_RE.fullmatch(n): add(fd,"P1","name",sf,"Bad name.","Fix.")
        elif n!=root.name: add(fd,"P1","name-mismatch",sf,f"{n}!={root.name}","Match.")
        d=fm.get("description","")
        if len(d.strip())<80: add(fd,"P1","desc",sf,"Too short.","Expand.")
    if "## Validation" not in t: add(fd,"P1","val",sf,"No validation.","Add.")
    if "## Escalation" not in t: add(fd,"P1","safety",sf,"No safety.","Add.")
    all_f=[p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    for p in all_f:
        rel=p.relative_to(root).as_posix(); c=p.read_text(encoding="utf-8",errors="replace")
        for ln in c.splitlines():
            if "SECRET_RE" in ln or "DANGEROUS" in ln: continue
            if SECRET_RE.search(ln): add(fd,"P0","secret",rel,"Secret.","Remove.");break
        for ln in c.splitlines():
            if "DANGEROUS" in ln: continue
            if DANGEROUS_RE.search(ln): add(fd,"P0","danger",rel,"Danger.","Remove.");break
    for m in LINK_RE.finditer(t):
        tgt=m.group(1).split("#",1)[0].strip()
        if not tgt or re.match(r"^(?:https?://|mailto:)",tgt): continue
        if not (root/tgt).exists(): add(fd,"P1","link",sf,f"Missing: {tgt}","Fix.")
    for m in RESOURCE_RE.finditer(t):
        tgt=m.group(1).strip()
        if not (root/tgt).exists(): add(fd,"P1","res",sf,f"Missing: {tgt}","Create.")
    validate_cr(root,fd,require=False)
    return result(root,fm,fd)
def validate_cr(root,fd,require=False):
    rr=root/"change-records"
    if not rr.exists():
        if require: add(fd,"P0","cr-missing",rr,"Missing records.","Create.")
        return
    idx=rr/"index.md"; cat=rr/"categories"; ent=rr/"entries"
    for p,r,m in [(idx,"cr-idx","Need index."),(cat,"cr-cat","Need categories."),(ent,"cr-ent","Need entries.")]:
        if not p.exists(): add(fd,"P0",r,p,m,"Create.")
    if idx.exists():
        t=idx.read_text(encoding="utf-8",errors="replace")
        for s in ["## Latest Changes","## Category Index","## Open Risks"]:
            if s not in t: add(fd,"P1","cr-idx-sec",idx,f"Missing {s}.","Add.")
        if not CHANGE_ID_RE.search(t): add(fd,"P1","cr-idx-id",idx,"No Change ID.","Add.")
    if cat.exists() and cat.is_dir():
        cf=sorted(cat.glob("*.md"))
        if not cf: add(fd,"P0","cr-no-cat",cat,"No ledgers.","Create.")
        for p in cf:
            t=p.read_text(encoding="utf-8",errors="replace")
            for s in ["## Purpose","## Outline","## Detailed Records"]:
                if s not in t: add(fd,"P1","cr-sec",p,f"Missing {s}.","Add.")
            if not CHANGE_ID_RE.search(t): add(fd,"P1","cr-id",p,"No ID.","Add.")
    if ent.exists() and ent.is_dir():
        df=sorted(ent.rglob("CR-*.md"))
        if not df: add(fd,"P0","cr-no-det",ent,"No detail.","Create.")
        seen=set()
        for p in df:
            rel=p.relative_to(root).as_posix()
            mt=CHANGE_ID_RE.search(p.name)
            if not mt: continue
            cid=mt.group(0)
            if cid in seen: add(fd,"P1","cr-dup",rel,f"Dup {cid}.","Fix.")
            seen.add(cid)
            t=p.read_text(encoding="utf-8",errors="replace")
            for s in ENTRY_SECTIONS:
                if s not in t: add(fd,"P1","cr-det-sec",rel,f"Missing {s}.","Add.")
def result(root,fm,fd):
    c={s:sum(1 for i in fd if i.severity==s) for s in ["P0","P1","P2"]}
    st="rejected" if c["P0"] else "review-required" if c["P1"] else "accepted-with-constraints"
    return {"skillRoot":str(root.resolve()),"frontmatter":fm,"summary":c,"status":st,"findings":[asdict(i) for i in fd]}
def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("skill_folder",type=Path)
    ap.add_argument("--json",type=Path)
    ap.add_argument("--require-change-records",action="store_true")
    a=ap.parse_args(argv)
    r=validate(a.skill_folder.resolve())
    if a.require_change_records:
        fd=[Finding(**i) for i in r["findings"]]; validate_cr(a.skill_folder.resolve(),fd,require=True); r=result(a.skill_folder.resolve(),r["frontmatter"],fd)
    if a.json: a.json.parent.mkdir(parents=True,exist_ok=True); a.json.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(r,ensure_ascii=False,indent=2))
    return 1 if r["summary"]["P0"] else 0
if __name__=="__main__": raise SystemExit(main())
