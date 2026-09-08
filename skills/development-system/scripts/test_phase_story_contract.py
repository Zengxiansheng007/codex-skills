"""Phase/Story contract tests for PH1-ST-001 ~ PH1-ST-004.

Validates:
- Positive phase-story fixture passes schema-level checks.
- Negative fixtures are rejected for missing FR/AC, missing entry/exit,
  missing testability/evidence, and dependency cycles.
- Requirement anchor and artifact envelope schemas have required fields.
"""
import json
import sys
from pathlib import Path


DEFAULT_ROOT = Path(__file__).resolve().parent.parent


def _load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _has_cycle(stories):
    """Detect cyclic dependencies among stories using DFS."""
    graph = {}
    for s in stories:
        sid = s.get("storyId", "")
        graph[sid] = s.get("dependsOn", [])
    visited = set()
    stack = set()

    def visit(node):
        if node in stack:
            return True
        if node in visited:
            return False
        visited.add(node)
        stack.add(node)
        for dep in graph.get(node, []):
            if dep in graph and visit(dep):
                return True
        stack.discard(node)
        return False

    for node in graph:
        if visit(node):
            return True
    return False


def _check_story_required_fields(story, label, errors):
    """Check that a story has all required fields non-empty."""
    for field in ["storyId", "title", "goal", "mappedRequirements", "acceptanceCriteria", "testability", "evidenceRequirements"]:
        val = story.get(field)
        if isinstance(val, list) and len(val) == 0:
            errors.append(f"{label}: {field} must not be empty")
        elif isinstance(val, str) and len(val.strip()) == 0:
            errors.append(f"{label}: {field} must not be empty")
        elif val is None:
            errors.append(f"{label}: {field} must not be None")


def test_positive_phase_story(root):
    errors = []
    fixture_path = root / "assets" / "fixtures" / "phase-story" / "phase1-positive.json"
    if not fixture_path.exists():
        return [f"positive fixture missing: {fixture_path}"]
    data = _load_json(fixture_path)
    phase = data.get("phase", {})
    if not phase.get("phaseId"):
        errors.append("positive fixture: phaseId missing")
    if not phase.get("entryCriteria"):
        errors.append("positive fixture: entryCriteria must not be empty")
    if not phase.get("exitCriteria"):
        errors.append("positive fixture: exitCriteria must not be empty")
    stories = phase.get("stories", [])
    if len(stories) < 4:
        errors.append(f"positive fixture: expected >=4 stories, got {len(stories)}")
    for s in stories:
        _check_story_required_fields(s, f"positive:{s.get('storyId','?')}", errors)
    if _has_cycle(stories):
        errors.append("positive fixture: dependency cycle detected (should not have one)")
    return errors


def test_negative_missing_fr_ac(root):
    errors = []
    fixture_path = root / "assets" / "fixtures" / "negative" / "NEG-STORY-001-missing-fr-ac.json"
    if not fixture_path.exists():
        return [f"negative fixture missing: {fixture_path}"]
    data = _load_json(fixture_path)
    story = data.get("story", {})
    # This story has empty mappedRequirements and acceptanceCriteria -> must be rejected.
    if story.get("mappedRequirements") != []:
        errors.append("NEG-STORY-001: mappedRequirements should be empty")
    if story.get("acceptanceCriteria") != []:
        errors.append("NEG-STORY-001: acceptanceCriteria should be empty")
    # Simulate validator rejection: if the story were valid, this would be a failure.
    is_rejected = len(story.get("mappedRequirements", [None])) == 0 or len(story.get("acceptanceCriteria", [None])) == 0
    if not is_rejected:
        errors.append("NEG-STORY-001: validator should reject missing FR/AC")
    return errors


def test_negative_missing_entry_exit(root):
    errors = []
    fixture_path = root / "assets" / "fixtures" / "negative" / "NEG-STORY-002-missing-entry-exit.json"
    if not fixture_path.exists():
        return [f"negative fixture missing: {fixture_path}"]
    data = _load_json(fixture_path)
    phase = data.get("phase", {})
    if phase.get("entryCriteria") != []:
        errors.append("NEG-STORY-002: entryCriteria should be empty")
    if phase.get("exitCriteria") != []:
        errors.append("NEG-STORY-002: exitCriteria should be empty")
    is_rejected = len(phase.get("entryCriteria", [None])) == 0 or len(phase.get("exitCriteria", [None])) == 0
    if not is_rejected:
        errors.append("NEG-STORY-002: validator should reject missing entry/exit")
    return errors


def test_negative_missing_testability_evidence(root):
    errors = []
    fixture_path = root / "assets" / "fixtures" / "negative" / "NEG-STORY-003-missing-testability-evidence.json"
    if not fixture_path.exists():
        return [f"negative fixture missing: {fixture_path}"]
    data = _load_json(fixture_path)
    story = data.get("story", {})
    testability = story.get("testability", "")
    evidence = story.get("evidenceRequirements", [])
    if testability != "":
        errors.append("NEG-STORY-003: testability should be empty string")
    if evidence != []:
        errors.append("NEG-STORY-003: evidenceRequirements should be empty")
    is_rejected = len(testability.strip()) == 0 or len(evidence) == 0
    if not is_rejected:
        errors.append("NEG-STORY-003: validator should reject missing testability/evidence")
    return errors


def test_negative_dependency_cycle(root):
    errors = []
    fixture_path = root / "assets" / "fixtures" / "negative" / "NEG-STORY-004-dependency-cycle.json"
    if not fixture_path.exists():
        return [f"negative fixture missing: {fixture_path}"]
    data = _load_json(fixture_path)
    phase = data.get("phase", {})
    stories = phase.get("stories", [])
    has_cycle = _has_cycle(stories)
    if not has_cycle:
        errors.append("NEG-STORY-004: dependency cycle not detected (should be detected)")
    return errors


def test_negative_ownership_clash(root):
    errors = []
    fixture_path = root / "assets" / "fixtures" / "negative" / "NEG-OWNERSHIP-001-private-profile-global-clash.json"
    if not fixture_path.exists():
        return [f"negative fixture missing: {fixture_path}"]
    data = _load_json(fixture_path)
    claim = data.get("ownershipClaim", {})
    if not claim.get("profileNamespace"):
        errors.append("NEG-OWNERSHIP-001: profileNamespace missing")
    if not claim.get("globalSkillName"):
        errors.append("NEG-OWNERSHIP-001: globalSkillName missing")
    if claim.get("conflictType") != "same-name-global-skill":
        errors.append("NEG-OWNERSHIP-001: conflictType should be same-name-global-skill")
    return errors


def test_schemas(root):
    errors = []
    # Requirement anchor schema
    anchor_path = root / "schemas" / "requirement-anchor.schema.json"
    if not anchor_path.exists():
        errors.append("requirement-anchor.schema.json missing")
    else:
        schema = _load_json(anchor_path)
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append("requirement-anchor.schema.json: must use draft 2020-12")
        props = schema.get("properties", {})
        if props.get("frAc", {}).get("minItems", 0) < 1:
            errors.append("requirement-anchor.schema.json: frAc must require minItems >= 1")
        if props.get("authorityOrder", {}).get("minItems", 0) < 1:
            errors.append("requirement-anchor.schema.json: authorityOrder must require minItems >= 1")
        required = schema.get("required", [])
        for field in ["anchorId", "version", "originalGoal", "approvedScope", "frAc", "authorityOrder"]:
            if field not in required:
                errors.append(f"requirement-anchor.schema.json: {field} must be in required")

    # Artifact envelope schema
    envelope_path = root / "schemas" / "artifact-envelope.schema.json"
    if not envelope_path.exists():
        errors.append("artifact-envelope.schema.json missing")
    else:
        schema = _load_json(envelope_path)
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append("artifact-envelope.schema.json: must use draft 2020-12")
        required = schema.get("required", [])
        for field in ["artifactId", "version", "artifactType", "owner", "sourceAnchorId", "sourceAnchorVersion", "mappedFrAc"]:
            if field not in required:
                errors.append(f"artifact-envelope.schema.json: {field} must be in required")

    # Phase-story schema
    phase_path = root / "schemas" / "phase-story.schema.json"
    if not phase_path.exists():
        errors.append("phase-story.schema.json missing")
    else:
        schema = _load_json(phase_path)
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append("phase-story.schema.json: must use draft 2020-12")
        required = schema.get("required", [])
        for field in ["phaseId", "entryCriteria", "exitCriteria", "stories"]:
            if field not in required:
                errors.append(f"phase-story.schema.json: {field} must be in required")
        story_def = schema.get("$defs", {}).get("story", {})
        story_required = story_def.get("required", [])
        for field in ["storyId", "mappedRequirements", "acceptanceCriteria", "dependsOn", "testability", "evidenceRequirements"]:
            if field not in story_required:
                errors.append(f"phase-story.schema.json story def: {field} must be in required")

    return errors


def main():
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_ROOT
    all_errors = []

    all_errors.extend(test_schemas(root))
    all_errors.extend(test_positive_phase_story(root))
    all_errors.extend(test_negative_missing_fr_ac(root))
    all_errors.extend(test_negative_missing_entry_exit(root))
    all_errors.extend(test_negative_missing_testability_evidence(root))
    all_errors.extend(test_negative_dependency_cycle(root))
    all_errors.extend(test_negative_ownership_clash(root))

    if all_errors:
        print("PHASE_STORY_CONTRACT_FAIL")
        for e in all_errors:
            print(f"  - {e}")
        return 1

    print("PHASE_STORY_CONTRACT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
