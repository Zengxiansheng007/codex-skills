import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
SCHEMA_PATH = SKILL_ROOT / "schemas" / "grill-session.schema.json"
FAILURE_CLASSIFICATION = SKILL_ROOT / "schemas" / "grill-failure-classification.json"

SENSITIVE_PATTERNS = [
    re.compile(r"(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{20,}"),
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


def _type_ok(value, expected):
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    return True


def validate_schema_node(schema, data, path="$"):
    """Minimal JSON Schema draft 2020-12 validator for the grill schema."""
    errors = []
    expected_type = schema.get("type")
    if expected_type:
        types = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(_type_ok(data, t) for t in types):
            return [f"{path}: expected {expected_type}"]
    if "const" in schema and data != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{path}: expected one of {schema['enum']!r}")
    if isinstance(data, str):
        if "minLength" in schema and len(data) < schema["minLength"]:
            errors.append(f"{path}: shorter than minLength {schema['minLength']}")
    if isinstance(data, list):
        if "minItems" in schema and len(data) < schema["minItems"]:
            errors.append(f"{path}: fewer than minItems {schema['minItems']}")
        if "items" in schema:
            for index, item in enumerate(data):
                errors.extend(validate_schema_node(schema["items"], item, f"{path}[{index}]"))
    if isinstance(data, dict):
        for key in schema.get("required", []):
            if key not in data:
                errors.append(f"{path}.{key}: missing required field")
        props = schema.get("properties", {})
        for key, subschema in props.items():
            if key in data:
                errors.extend(validate_schema_node(subschema, data[key], f"{path}.{key}"))
    return errors


def check_schema(data):
    """Validate the parsed session against grill-session.schema.json."""
    findings = []
    if data.get("schemaVersion") == "2.0":
        from grill_session_runtime import validate_ledger  # V2 semantics include closure and legacy-write boundaries.
        for issue in validate_ledger(data, intent="read"):
            add(findings, issue["severity"], issue["rule"], issue["message"])
        return findings
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        errors = validate_schema_node(schema, data)
        for err in errors:
            add(findings, "P0", "schema-violation", err)
    except OSError as exc:
        add(findings, "P1", "schema-load-failed", f"Could not load schema: {exc}")
    except json.JSONDecodeError as exc:
        add(findings, "P1", "schema-load-failed", f"Could not parse schema: {exc}")
    return findings


def check_failure_class_stability():
    """Verify grill failure classes never propagate to completed."""
    findings = []
    try:
        fc = json.loads(FAILURE_CLASSIFICATION.read_text(encoding="utf-8"))
        for cls in fc.get("classes", []):
            if cls.get("propagation") == "completed":
                add(findings, "P0", "failure-class-propagates-to-completed",
                    f"Failure class {cls.get('name')} maps to completed.")
    except OSError:
        pass  # Optional check; failure classification may be absent.
    return findings


def validate(data, raw, allow_template=False):
    findings = []

    # Schema validation against grill-session.schema.json
    findings.extend(check_schema(data))

    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(raw):
            add(findings, "P0", "sensitive-data", "report contains a secret-like or credential-like value")
            break

    if data.get("schemaVersion") == "2.0":
        return findings  # V2 report semantics are owned by the canonical ledger validator.

    missing = sorted(REQUIRED_TOP_LEVEL - set(data))
    if missing:
        add(findings, "P0", "missing-top-level-fields", f"missing fields: {', '.join(missing)}")
        return findings

    # Formal session: sessionId must be non-empty (AC-003)
    session_id = data.get("sessionId")
    if not isinstance(session_id, str) or not session_id.strip():
        add(findings, "P0", "session-id-missing", "sessionId must be a non-empty formal identifier")

    if data.get("status") not in VALID_STATUSES:
        add(findings, "P0", "invalid-session-status", f"invalid status: {data.get('status')}")

    questions = data.get("questions")
    if not isinstance(questions, list):
        add(findings, "P0", "invalid-questions", "questions must be a list")
        return findings

    if not allow_template and not questions:
        add(findings, "P0", "no-questions-in-non-template", "non-template report must contain at least one question")

    for idx, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            add(findings, "P0", "invalid-question", f"question #{idx} must be an object")
            continue
        missing_q = sorted(REQUIRED_QUESTION_FIELDS - set(question))
        if missing_q:
            add(findings, "P0", "missing-required-question-field",
                f"{question.get('id', idx)} missing: {', '.join(missing_q)}")
        if question.get("status") not in VALID_QUESTION_STATUSES:
            add(findings, "P1", "invalid-question-status",
                f"{question.get('id', idx)} invalid status: {question.get('status')}")
        if question.get("severity") not in VALID_SEVERITIES:
            add(findings, "P1", "invalid-question-severity",
                f"{question.get('id', idx)} invalid severity: {question.get('severity')}")
        text = str(question.get("question", ""))
        question_marks = text.count("?") + text.count("？")
        if question_marks > 1:
            add(findings, "P1", "multiple-questions-in-one",
                f"{question.get('id', idx)} appears to ask more than one question")
        if not str(question.get("recommendedAnswer", "")).strip():
            add(findings, "P0", "missing-recommended-answer",
                f"{question.get('id', idx)} has no recommended answer")

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

    # Check failure class stability (never propagates to completed)
    findings.extend(check_failure_class_stability())

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
