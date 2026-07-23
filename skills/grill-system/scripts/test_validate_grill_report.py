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
    assert "missing-question-fields" in result.stdout


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
    assert "multiple-questions" in result.stdout


def test_secret_like_value_fails(tmp):
    session = valid_session()
    secret = "sk-" + "A" * 24
    session["evidenceIndex"][0]["claim"] = secret
    path = tmp / "secret.html"
    path.write_text(html_with_session(session), encoding="utf-8")
    result = run_validator(path)
    assert result.returncode != 0
    assert "sensitive-data" in result.stdout


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        test_valid_report_passes(tmp)
        test_template_allowed()
        test_missing_question_fails(tmp)
        test_complete_with_p0_open_item_fails(tmp)
        test_multiple_questions_warns_but_does_not_fail(tmp)
        test_secret_like_value_fails(tmp)
    print("ok: grill report validator tests passed")
