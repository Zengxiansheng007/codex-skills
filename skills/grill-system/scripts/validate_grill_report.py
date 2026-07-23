import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


SENSITIVE_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]+", re.IGNORECASE),
    re.compile(r"pass" + r"word\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"tok" + r"en\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"coo" + r"kie\s*[:=]\s*\S+", re.IGNORECASE),
]

REQUIRED_TOP_LEVEL = {
    "sessionId",
    "scenario",
    "status",
    "questions",
    "decisions",
    "evidenceIndex",
    "openItems",
    "nextActions",
}

REQUIRED_QUESTION_FIELDS = {
    "id",
    "question",
    "purpose",
    "recommendedAnswer",
    "blockingDecision",
    "status",
    "severity",
}

VALID_STATUSES = {"draft", "blocked", "complete", "risk-accepted"}
VALID_QUESTION_STATUSES = {"proposed", "confirmed", "changed", "rejected", "needs-evidence"}
VALID_SEVERITIES = {"P0", "P1", "P2"}


class ScriptJsonParser(HTMLParser):
    def __init__(self, target_id):
        super().__init__()
        self.target_id = target_id
        self.in_target = False
        self.chunks = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag.lower() == "script" and attrs_dict.get("id") == self.target_id:
            self.in_target = True

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self.in_target:
            self.in_target = False

    def handle_data(self, data):
        if self.in_target:
            self.chunks.append(data)


def extract_session(path):
    raw = Path(path).read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(raw), raw
    parser = ScriptJsonParser("grill-session")
    parser.feed(raw)
    if not parser.chunks:
        raise ValueError("missing <script type=\"application/json\" id=\"grill-session\"> block")
    json_text = "".join(parser.chunks).strip()
    return json.loads(json_text), raw


def add(findings, severity, rule, message):
    findings.append({"severity": severity, "rule": rule, "message": message})


def validate(data, raw, allow_template=False):
    findings = []

    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(raw):
            add(findings, "P0", "sensitive-data", "report contains a secret-like or credential-like value")
            break

    missing = sorted(REQUIRED_TOP_LEVEL - set(data))
    if missing:
        add(findings, "P0", "missing-top-level-fields", f"missing fields: {', '.join(missing)}")
        return findings

    if data.get("status") not in VALID_STATUSES:
        add(findings, "P0", "invalid-session-status", f"invalid status: {data.get('status')}")

    questions = data.get("questions")
    if not isinstance(questions, list):
        add(findings, "P0", "invalid-questions", "questions must be a list")
        return findings

    if not allow_template and not questions:
        add(findings, "P0", "no-questions", "non-template report must contain at least one question")

    for idx, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            add(findings, "P0", "invalid-question", f"question #{idx} must be an object")
            continue
        missing_q = sorted(REQUIRED_QUESTION_FIELDS - set(question))
        if missing_q:
            add(findings, "P0", "missing-question-fields", f"{question.get('id', idx)} missing: {', '.join(missing_q)}")
        if question.get("status") not in VALID_QUESTION_STATUSES:
            add(findings, "P1", "invalid-question-status", f"{question.get('id', idx)} invalid status: {question.get('status')}")
        if question.get("severity") not in VALID_SEVERITIES:
            add(findings, "P1", "invalid-question-severity", f"{question.get('id', idx)} invalid severity: {question.get('severity')}")
        text = str(question.get("question", ""))
        question_marks = text.count("?") + text.count("？")
        if question_marks > 1:
            add(findings, "P1", "multiple-questions", f"{question.get('id', idx)} appears to ask more than one question")
        if not str(question.get("recommendedAnswer", "")).strip():
            add(findings, "P0", "missing-recommended-answer", f"{question.get('id', idx)} has no recommended answer")

    open_items = data.get("openItems")
    if not isinstance(open_items, list):
        add(findings, "P0", "invalid-open-items", "openItems must be a list")
    else:
        p0_open = [item for item in open_items if isinstance(item, dict) and item.get("severity") == "P0"]
        if p0_open and data.get("status") == "complete":
            add(findings, "P0", "complete-with-p0-open-items", "complete sessions cannot contain P0 open items")

    for list_field in ("decisions", "evidenceIndex", "nextActions"):
        if not isinstance(data.get(list_field), list):
            add(findings, "P0", f"invalid-{list_field}", f"{list_field} must be a list")

    return findings


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    parser.add_argument("--allow-template", action="store_true")
    parser.add_argument("--json", dest="json_output")
    args = parser.parse_args(argv)

    try:
        data, raw = extract_session(Path(args.report))
        findings = validate(data, raw, allow_template=args.allow_template)
    except Exception as exc:
        findings = [{"severity": "P0", "rule": "parse-error", "message": str(exc)}]

    summary = {
        "P0": sum(1 for f in findings if f["severity"] == "P0"),
        "P1": sum(1 for f in findings if f["severity"] == "P1"),
        "P2": sum(1 for f in findings if f["severity"] == "P2"),
    }
    result = {"summary": summary, "findings": findings}

    if args.json_output:
        Path(args.json_output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if summary["P0"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
