import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_grill_report.py"


def run_validator(path, *extra):
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(path), *extra],
        text=True,
        capture_output=True,
        check=False,
    )


def html_with_session(session):
    return f"""<!doctype html>
<html><body>
<script type="application/json" id="grill-session">
{json.dumps(session, ensure_ascii=False)}
</script>
</body></html>"""


def valid_session():
    return {
        "sessionId": "grill-test",
        "scenario": "test-case-design",
        "status": "complete",
        "sourceInputs": [],
        "questions": [
            {
                "id": "Q-001",
                "question": "Which source is authoritative for current behavior?",
                "purpose": "Choose the test oracle.",
                "evidence": ["E-001"],
                "recommendedAnswer": "Use running behavior as current truth and mark document drift as a risk.",
                "blockingDecision": "oracle source",
                "userResponse": "confirmed",
                "status": "confirmed",
                "severity": "P0",
            }
        ],
        "decisions": [],
        "evidenceIndex": [{"id": "E-001", "type": "report", "pathOrUrl": "local", "claim": "sample"}],
        "openItems": [],
        "nextActions": [],
    }


def test_valid_report_passes(tmp):
    path = tmp / "valid.html"
    path.write_text(html_with_session(valid_session()), encoding="utf-8")
    result = run_validator(path)
    assert result.returncode == 0, result.stdout + result.stderr


def test_template_allowed():
    template = ROOT / "assets" / "grill-report-template.html"
    result = run_validator(template, "--allow-template")
    assert result.returncode == 0, result.stdout + result.stderr


def test_missing_question_fails(tmp):
    session = valid_session()
    del session["questions"][0]["recommendedAnswer"]
    path = tmp / "bad.html"
    path.write_text(html_with_session(session), encoding="utf-8")
    result = run_validator(path)
    assert result.returncode != 0
    assert "missing-required-question-field" in result.stdout or "schema-violation" in result.stdout


def test_complete_with_p0_open_item_fails(tmp):
    session = valid_session()
    session["openItems"] = [{"id": "O-001", "severity": "P0", "question": "blocked"}]
    path = tmp / "p0-open.html"
    path.write_text(html_with_session(session), encoding="utf-8")
    result = run_validator(path)
    assert result.returncode != 0
    assert "complete-with-p0-open-items" in result.stdout


def test_multiple_questions_warns_but_does_not_fail(tmp):
    session = valid_session()
    session["questions"][0]["question"] = "What is the oracle? Who approves it?"
    path = tmp / "multi.html"
    path.write_text(html_with_session(session), encoding="utf-8")
    result = run_validator(path)
    assert result.returncode == 0
    assert "multiple-questions-in-one" in result.stdout


def test_secret_like_value_fails(tmp):
    session = valid_session()
    secret = "sk-" + "A" * 24
    session["evidenceIndex"][0]["claim"] = secret
    path = tmp / "secret.html"
    path.write_text(html_with_session(session), encoding="utf-8")
    result = run_validator(path)
    assert result.returncode != 0
    assert "sensitive-data" in result.stdout


def test_empty_session_id_fails(tmp):
    """AC-003: Formal session requires non-empty sessionId."""
    session = valid_session()
    session["sessionId"] = ""
    path = tmp / "empty-session-id.html"
    path.write_text(html_with_session(session), encoding="utf-8")
    result = run_validator(path)
    assert result.returncode != 0
    assert "session-id-missing" in result.stdout


def test_invalid_session_status_fails(tmp):
    """AC-003: Invalid session status is rejected."""
    session = valid_session()
    session["status"] = "finished"
    path = tmp / "invalid-status.html"
    path.write_text(html_with_session(session), encoding="utf-8")
    result = run_validator(path)
    assert result.returncode != 0
    assert "invalid-session-status" in result.stdout or "schema-violation" in result.stdout


def test_json_direct_validation(tmp):
    """AC-004: Validator accepts a plain .json file with a valid session."""
    session = valid_session()
    path = tmp / "valid.json"
    path.write_text(json.dumps(session, ensure_ascii=False), encoding="utf-8")
    result = run_validator(path)
    assert result.returncode == 0, result.stdout + result.stderr


def test_invalid_question_status_fails(tmp):
    """AC-004: Invalid question status is flagged as P1."""
    session = valid_session()
    session["questions"][0]["status"] = "answered"
    path = tmp / "invalid-q-status.html"
    path.write_text(html_with_session(session), encoding="utf-8")
    result = run_validator(path)
    assert result.returncode != 0
    assert "invalid-question-status" in result.stdout or "schema-violation" in result.stdout


def test_invalid_question_severity_fails(tmp):
    """AC-004: Invalid question severity is flagged as P1."""
    session = valid_session()
    session["questions"][0]["severity"] = "P3"
    path = tmp / "invalid-severity.html"
    path.write_text(html_with_session(session), encoding="utf-8")
    result = run_validator(path)
    assert result.returncode != 0
    assert "invalid-question-severity" in result.stdout or "schema-violation" in result.stdout


def test_no_questions_in_non_template_fails(tmp):
    """AC-011: A non-template report with zero questions fails."""
    session = valid_session()
    session["questions"] = []
    path = tmp / "no-questions.html"
    path.write_text(html_with_session(session), encoding="utf-8")
    result = run_validator(path)
    assert result.returncode != 0
    assert "no-questions-in-non-template" in result.stdout or "schema-violation" in result.stdout


def test_risk_accepted_with_p0_open_allowed(tmp):
    """AC-003: risk-accepted status allows P0 open items (explicit risk acceptance)."""
    session = valid_session()
    session["status"] = "risk-accepted"
    session["openItems"] = [{"id": "O-001", "severity": "P0", "question": "blocked"}]
    path = tmp / "risk-accepted.html"
    path.write_text(html_with_session(session), encoding="utf-8")
    result = run_validator(path)
    assert result.returncode == 0, result.stdout + result.stderr


def test_failure_classification_never_completes():
    """AC-011: No grill failure class propagates to completed."""
    fc_path = ROOT / "schemas" / "grill-failure-classification.json"
    fc = json.loads(fc_path.read_text(encoding="utf-8"))
    for cls in fc.get("classes", []):
        assert cls["propagation"] != "completed", \
            f"{cls['name']} must not propagate to completed"
    print("  PASS: no grill failure class propagates to completed")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        test_valid_report_passes(tmp)
        test_template_allowed()
        test_missing_question_fails(tmp)
        test_complete_with_p0_open_item_fails(tmp)
        test_multiple_questions_warns_but_does_not_fail(tmp)
        test_secret_like_value_fails(tmp)
        test_empty_session_id_fails(tmp)
        test_invalid_session_status_fails(tmp)
        test_json_direct_validation(tmp)
        test_invalid_question_status_fails(tmp)
        test_invalid_question_severity_fails(tmp)
        test_no_questions_in_non_template_fails(tmp)
        test_risk_accepted_with_p0_open_allowed(tmp)
    test_failure_classification_never_completes()
    print("ok: grill report validator tests passed")
