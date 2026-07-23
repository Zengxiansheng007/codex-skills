import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED = {
    "documentType": "P0",
    "sourceBaseline": "P0",
    "moduleUnderstanding": "P0",
    "businessObjects": "P0",
    "upstreamDownstream": "P0",
    "evidenceContract": "P0",
    "acceptanceCriteria": "P0",
    "riskAndSafety": "P0",
    "handoffTargets": "P1",
    "openQuestions": "P1",
}


def fail(message):
    print(f"FAIL: {message}")
    sys.exit(1)


def validate_doc(doc):
    for key, severity in REQUIRED.items():
        if key not in doc:
            fail(f"missing {severity} field: {key}")
    if not isinstance(doc["businessObjects"], list) or not doc["businessObjects"]:
        fail("businessObjects must be a non-empty list")
    if not doc["evidenceContract"].get("evidenceIndexRequired"):
        fail("evidenceContract.evidenceIndexRequired must be true")
    for action in doc["riskAndSafety"].get("forbiddenActions", []):
        if action.lower() in {"delete", "publish", "deploy", "pay", "approve"}:
            continue
    targets = doc["handoffTargets"]
    for target in ["developmentPlan", "testPlan", "testcaseGenerator", "uiTest"]:
        if target not in targets:
            fail(f"missing handoff target: {target}")


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "assets" / "forward-tests" / "agent-ready-valid.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    validate_doc(doc)

    schema_ref = (ROOT / "references" / "agent-ready-output-schema.md").read_text(encoding="utf-8")
    boundary_ref = (ROOT / "references" / "capability-boundary-map.md").read_text(encoding="utf-8")
    governance_ref = (ROOT / "references" / "governance-diagnostics.md").read_text(encoding="utf-8")
    for phrase in [
        "Agent-ready Output Schema",
        "Required Top-level Fields",
        "Handoff Rules",
        "Grill Triggers",
    ]:
        if phrase not in schema_ref:
            fail(f"schema reference missing phrase: {phrase}")
    for phrase in ["Handoff to development-plan", "Handoff to test-plan", "Handoff to testcase-generator", "Handoff to ui-test"]:
        if phrase not in boundary_ref:
            fail(f"boundary reference missing phrase: {phrase}")
    for phrase in ["Change Impact Analysis", "Failure Diagnosis Library", "Memory Governance"]:
        if phrase not in governance_ref:
            fail(f"governance reference missing phrase: {phrase}")
    print("PASS: agent-ready schema and boundary references validated")


if __name__ == "__main__":
    main()
