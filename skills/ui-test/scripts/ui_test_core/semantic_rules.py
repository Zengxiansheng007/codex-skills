"""Semantic Rule Registry and stable Issue List for Source Case validation.

This module runs *after* structural schema validation but *before* Case IR
lowering.  It catches cross-field business-fact errors that JSON Schema
cannot express: wrong content-component variant, popup-version assertion
mismatch, missing P0 responsibility, R2 one-submit boundary violations,
shared-data index_ref problems, and ``<br>`` parameter aggregation.

Each issue is a stable, machine-readable dict with keys:
    issue_id, rule_id, severity, case_id, branch_id, source_path,
    message, expected, actual, suggested_fix, blocking, evidence_refs

The list is sorted by (severity_order, case_id, branch_id, rule_id,
source_path, issue_id) so that repeated runs on the same Source Case
produce byte-identical output (determinism / NFR-TOTAL-001).
"""

from __future__ import annotations

import re
from typing import Any, Callable

# Severity ordering: P0 first, then P1, P2, info
_SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "info": 3}
_BLOCKING_SEVERITIES = {"P0", "P1"}

# Branch definitions per the approved Grill decisions:
#   A = system announcement  -> plain text input (plain-content component)
#   B = homepage popup        -> rich text editor (rich-content component)
BRANCH_COMPONENT_MAP = {
    "system-announcement": {"expected_component": "component.plain-content", "component_variant": "plain-text", "accepted_variants": {"plain-text", "system-plain-text"}, "label": "A"},
    "homepage-popup": {"expected_component": "component.rich-content", "component_variant": "rich-text", "accepted_variants": {"rich-text", "popup-rich-text"}, "label": "B"},
    "popup-announcement": {"expected_component": "component.rich-content", "component_variant": "rich-text", "accepted_variants": {"rich-text", "popup-rich-text"}, "label": "B"},
}

# Reverse lookup by label
LABEL_TO_BRANCH = {"A": "system-announcement", "B": "homepage-popup"}


def _branch_label(branch_id: str | None) -> str:
    if not branch_id:
        return ""
    if branch_id in BRANCH_COMPONENT_MAP:
        return BRANCH_COMPONENT_MAP[branch_id]["label"]
    for bid, info in BRANCH_COMPONENT_MAP.items():
        if info["label"] == branch_id:
            return branch_id
    return ""


def _branch_info(branch_id: str | None) -> dict[str, Any] | None:
    if not branch_id:
        return None
    if branch_id in BRANCH_COMPONENT_MAP:
        return BRANCH_COMPONENT_MAP[branch_id]
    for bid, info in BRANCH_COMPONENT_MAP.items():
        if info["label"] == branch_id:
            return info
    return None


def _make_issue(
    issue_id: str, rule_id: str, severity: str, case_id: str,
    branch_id: str | None, source_path: str, message: str,
    expected: str, actual: str, suggested_fix: str,
    evidence_refs: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "issue_id": issue_id,
        "rule_id": rule_id,
        "severity": severity,
        "case_id": case_id,
        "branch_id": branch_id,
        "source_path": source_path,
        "message": message,
        "expected": expected,
        "actual": actual,
        "suggested_fix": suggested_fix,
        "blocking": severity in _BLOCKING_SEVERITIES,
        "evidence_refs": evidence_refs or [],
    }


# -- Rule functions ---------------------------------------------------------

def _rule_scope_consistency(sc: dict[str, Any], _ctx: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    case_id = sc.get("case_id", "unknown")
    branch_id = sc.get("branch_id")
    scope = sc.get("scope", {})
    if not isinstance(scope, dict):
        return issues
    module_path = scope.get("module_path", [])
    function = scope.get("function", "")
    # The function should be "create" for announcement creation cases
    if function and function not in {"create", "edit", "delete", "view", "publish", "review"}:
        issues.append(_make_issue(
            issue_id=f"SEM-SCOPE-001-{case_id}",
            rule_id="SEM-SCOPE-001",
            severity="P1",
            case_id=case_id,
            branch_id=branch_id,
            source_path="/scope/function",
            message=f"scope.function '{function}' is not in the known function set",
            expected="one of: create, edit, delete, view, publish, review",
            actual=function,
            suggested_fix="correct scope.function to match a known announcement operation",
        ))
    # Check that module_path contains announcement-related segment if branch is announcement
    if branch_id == "system-announcement" or _branch_label(branch_id) == "A":
        path_str = "/".join(module_path) if isinstance(module_path, list) else ""
        if "announcement" not in path_str.lower():
            issues.append(_make_issue(
                issue_id=f"SEM-SCOPE-002-{case_id}",
                rule_id="SEM-SCOPE-002",
                severity="P1",
                case_id=case_id,
                branch_id=branch_id,
                source_path="/scope/module_path",
                message="system-announcement branch must have 'announcement' in module_path",
                expected="module_path containing 'announcement'",
                actual=path_str,
                suggested_fix="add 'announcement' to scope.module_path",
            ))
    return issues


def _rule_case_display_name(sc: dict[str, Any], _ctx: dict[str, Any]) -> list[dict[str, Any]]:
    """Require a governed human-facing Chinese case name distinct from its ID."""
    case_id = sc.get("case_id", "unknown")
    branch_id = sc.get("branch_id")
    display_name = str(sc.get("display_name", "")).strip()
    if not display_name:
        return [_make_issue(
            issue_id=f"SEM-DISPLAY-001-{case_id}",
            rule_id="SEM-DISPLAY-001",
            severity="P1",
            case_id=case_id,
            branch_id=branch_id,
            source_path="/display_name",
            message="case display_name is required for Human View and XMind",
            expected="a governed Chinese display name",
            actual="missing or blank",
            suggested_fix="add Source Case display_name from the approved project naming registry",
        )]
    if display_name == case_id or re.fullmatch(r"[A-Z0-9][A-Z0-9._-]{2,127}", display_name):
        return [_make_issue(
            issue_id=f"SEM-DISPLAY-002-{case_id}",
            rule_id="SEM-DISPLAY-002",
            severity="P1",
            case_id=case_id,
            branch_id=branch_id,
            source_path="/display_name",
            message="case display_name must not be a Stable ID",
            expected="a human-facing Chinese business name",
            actual=display_name,
            suggested_fix="replace the Stable ID with the confirmed Chinese case name",
        )]
    if not re.search(r"[\u4e00-\u9fff]", display_name):
        return [_make_issue(
            issue_id=f"SEM-DISPLAY-003-{case_id}",
            rule_id="SEM-DISPLAY-003",
            severity="P1",
            case_id=case_id,
            branch_id=branch_id,
            source_path="/display_name",
            message="case display_name must contain a Chinese business name",
            expected="display_name containing Chinese characters",
            actual=display_name,
            suggested_fix="set display_name using the approved Chinese naming registry",
        )]
    return []


def _rule_content_component_variant(sc: dict[str, Any], _ctx: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    case_id = sc.get("case_id", "unknown")
    branch_id = sc.get("branch_id")
    binfo = _branch_info(branch_id)
    if not binfo:
        return issues
    expected_component = binfo["expected_component"]
    expected_variant = binfo["component_variant"]
    label = binfo["label"]
    component_refs = sc.get("component_refs", [])
    actual_components = [ref.get("id", "") if isinstance(ref, dict) else str(ref) for ref in component_refs]
    test_points = sc.get("test_points", [])
    actual_variants = [tp.get("variant", "") if isinstance(tp, dict) else "" for tp in test_points]
    # Check component_refs
    if expected_component not in actual_components:
        issues.append(_make_issue(
            issue_id=f"SEM-VARIANT-001-{case_id}",
            rule_id="SEM-VARIANT-001",
            severity="P0",
            case_id=case_id,
            branch_id=branch_id,
            source_path="/component_refs",
            message=f"branch {label} ({branch_id}) must use {expected_component}, found {actual_components}",
            expected=expected_component,
            actual=", ".join(actual_components) if actual_components else "none",
            suggested_fix=f"replace content component with {expected_component} for branch {label}",
        ))
    # Check test_point variant
    accepted_variants = binfo.get("accepted_variants", {expected_variant})
    if not accepted_variants.intersection(actual_variants):
        issues.append(_make_issue(
            issue_id=f"SEM-VARIANT-002-{case_id}",
            rule_id="SEM-VARIANT-002",
            severity="P0",
            case_id=case_id,
            branch_id=branch_id,
            source_path="/test_points",
            message=f"branch {label} ({branch_id}) must declare variant '{expected_variant}'",
            expected=expected_variant,
            actual=", ".join(actual_variants) if actual_variants else "none",
            suggested_fix=f"set test_point variant to '{expected_variant}' for branch {label}",
        ))
    return issues


def _rule_assertion_target_mismatch(sc: dict[str, Any], _ctx: dict[str, Any]) -> list[dict[str, Any]]:
    """Assert that assertion steps don't check wrong popup-version or content-version.

    A branch should not assert 'popup version visible' (that's B's concern)
    and B should not assert 'plain content matches' without rich-text context.
    """
    issues: list[dict[str, Any]] = []
    case_id = sc.get("case_id", "unknown")
    branch_id = sc.get("branch_id")
    binfo = _branch_info(branch_id)
    if not binfo:
        return issues
    label = binfo["label"]
    expected_variant = binfo["component_variant"]
    assertions = sc.get("steps", {}).get("assertions", [])
    for idx, step in enumerate(assertions):
        if not isinstance(step, dict):
            continue
        intent = step.get("intent", "")
        expected_result = step.get("expected_result", "")
        text = " ".join(_text_variants(f"{intent} {expected_result}")).lower()
        # A (system-announcement, plain-text) should not assert popup-version
        popup_version = ("popup" in text and "version" in text) or ("\u5f39\u7a97" in text and "\u7248\u672c" in text)
        plain_content = ("plain" in text and "content" in text) or ("\u666e\u901a" in text and "\u6587\u672c" in text and "\u5185\u5bb9" in text)
        if label == "A" and popup_version:
            issues.append(_make_issue(
                issue_id=f"SEM-ASSERT-001-{case_id}-{idx}",
                rule_id="SEM-ASSERT-001",
                severity="P0",
                case_id=case_id,
                branch_id=branch_id,
                source_path=f"/steps/assertions/{idx}/expected_result",
                message="branch A must not assert popup-version; popup version is branch B's concern",
                expected="plain-text content assertion",
                actual=f"popup-version assertion: {expected_result}",
                suggested_fix="replace popup-version assertion with plain-content assertion",
            ))
        # B (homepage-popup, rich-text) should not assert plain-content matches
        if label == "B" and (plain_content and ("matches" in text or "\u5339\u914d" in text)):
            issues.append(_make_issue(
                issue_id=f"SEM-ASSERT-002-{case_id}-{idx}",
                rule_id="SEM-ASSERT-002",
                severity="P0",
                case_id=case_id,
                branch_id=branch_id,
                source_path=f"/steps/assertions/{idx}/expected_result",
                message="branch B must not assert plain-content matches; plain text is branch A's concern",
                expected="rich-text content assertion",
                actual=f"plain-content assertion: {expected_result}",
                suggested_fix="replace plain-content assertion with rich-text content assertion",
            ))
    return issues


def _text_variants(value: str) -> list[str]:
    """Return raw text plus the common UTF-8-as-GBK repair view.

    Some legacy assets were decoded with the wrong Windows code page.  The
    repair view is used only for semantic matching; source material is never
    rewritten implicitly.
    """
    variants = [value]
    try:
        repaired = value.encode("gb18030").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        repaired = ""
    if repaired and repaired != value:
        variants.append(repaired)
    return variants


def _rule_p0_responsibility(sc: dict[str, Any], _ctx: dict[str, Any]) -> list[dict[str, Any]]:
    """P0 cases must have at least one test_point with responsibility='primary'."""
    issues: list[dict[str, Any]] = []
    case_id = sc.get("case_id", "unknown")
    branch_id = sc.get("branch_id")
    priority = sc.get("priority", "")
    test_points = sc.get("test_points", [])
    if priority == "P0":
        has_primary = any(
            isinstance(tp, dict) and tp.get("responsibility") == "primary"
            for tp in test_points
        )
        if not has_primary:
            issues.append(_make_issue(
                issue_id=f"SEM-P0-001-{case_id}",
                rule_id="SEM-P0-001",
                severity="P0",
                case_id=case_id,
                branch_id=branch_id,
                source_path="/test_points",
                message="P0 case must have at least one test_point with responsibility='primary'",
                expected="at least one test_point with responsibility=primary",
                actual="no primary responsibility test_point found",
                suggested_fix="add or change a test_point responsibility to 'primary'",
            ))
    return issues


def validate_p0_suite(source_cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate joint P0 coverage across branches in the same suite.

    Variant test points such as ``announcement-content/plain`` and
    ``announcement-content/rich`` belong to the same coverage family.  A
    family may be declared not-applicable in one branch only when another
    branch provides an active responsibility for that family.
    """
    grouped: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for source_case in source_cases:
        if source_case.get("priority") != "P0":
            continue
        suite_id = source_case.get("p0_suite_id") or "<missing-suite>"
        for point in source_case.get("test_points", []):
            if not isinstance(point, dict):
                continue
            point_id = str(point.get("test_point_id", ""))
            family = point_id.split("/", 1)[0]
            grouped.setdefault(suite_id + "|" + family, []).append((source_case, point))
    issues: list[dict[str, Any]] = []
    for key, members in sorted(grouped.items()):
        has_active = any(
            point.get("responsibility") in {"primary", "supporting"}
            and point.get("coverage_method") != "not-applicable"
            for _, point in members
        )
        if has_active:
            continue
        suite_id, family = key.split("|", 1)
        case_id = members[0][0].get("case_id", "unknown")
        issues.append(_make_issue(
            issue_id=f"SEM-P0-002-{suite_id}-{family}",
            rule_id="SEM-P0-002",
            severity="P0",
            case_id=case_id,
            branch_id=members[0][0].get("branch_id"),
            source_path="/test_points",
            message=f"P0 coverage family '{family}' has no active responsibility across its suite",
            expected="at least one primary or supporting test point in the suite",
            actual="all declared variants are not-applicable or execution-only",
            suggested_fix="add a branch that actively operates or asserts this coverage family",
        ))
    return issues


def _rule_r2_ui_only_one_submit(sc: dict[str, Any], _ctx: dict[str, Any]) -> list[dict[str, Any]]:
    """R2 risk_level must have ui_only=true, max_submit_count=1, and environment contains 'test'."""
    issues: list[dict[str, Any]] = []
    case_id = sc.get("case_id", "unknown")
    branch_id = sc.get("branch_id")
    risk = sc.get("risk", {})
    if not isinstance(risk, dict):
        return issues
    risk_level = risk.get("risk_level", "")
    if risk_level != "R2":
        return issues
    if risk.get("ui_only") is not True:
        issues.append(_make_issue(
            issue_id=f"SEM-R2-001-{case_id}",
            rule_id="SEM-R2-001",
            severity="P0",
            case_id=case_id,
            branch_id=branch_id,
            source_path="/risk/ui_only",
            message="R2 risk must have ui_only=true",
            expected="true",
            actual=str(risk.get("ui_only")),
            suggested_fix="set risk.ui_only to true",
        ))
    if risk.get("max_submit_count") != 1:
        issues.append(_make_issue(
            issue_id=f"SEM-R2-002-{case_id}",
            rule_id="SEM-R2-002",
            severity="P0",
            case_id=case_id,
            branch_id=branch_id,
            source_path="/risk/max_submit_count",
            message="R2 risk must have max_submit_count=1 (one-submit boundary)",
            expected="1",
            actual=str(risk.get("max_submit_count")),
            suggested_fix="set risk.max_submit_count to 1",
        ))
    env_allow = risk.get("environment_allowlist", [])
    if "test" not in env_allow:
        issues.append(_make_issue(
            issue_id=f"SEM-R2-003-{case_id}",
            rule_id="SEM-R2-003",
            severity="P0",
            case_id=case_id,
            branch_id=branch_id,
            source_path="/risk/environment_allowlist",
            message="R2 risk environment_allowlist must contain 'test'",
            expected="['test'] or includes 'test'",
            actual=str(env_allow),
            suggested_fix="add 'test' to risk.environment_allowlist",
        ))
    return issues


def _rule_shared_data_index_refs(sc: dict[str, Any], _ctx: dict[str, Any]) -> list[dict[str, Any]]:
    """shared-data and public-data parameters must have non-empty index_ref."""
    issues: list[dict[str, Any]] = []
    case_id = sc.get("case_id", "unknown")
    branch_id = sc.get("branch_id")
    steps_obj = sc.get("steps", {})
    for section in ("setup", "feature", "assertions"):
        steps = steps_obj.get(section, []) if isinstance(steps_obj, dict) else []
        for s_idx, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            step_id = step.get("step_id", f"unknown-{section}-{s_idx}")
            parameters = step.get("parameters", [])
            if not isinstance(parameters, list):
                continue
            for p_idx, param in enumerate(parameters):
                if not isinstance(param, dict):
                    continue
                source_type = param.get("source_type", "")
                if source_type in ("shared-data", "public-data"):
                    index_ref = param.get("index_ref", "")
                    if not isinstance(index_ref, str) or not index_ref.strip():
                        issues.append(_make_issue(
                            issue_id=f"SEM-DATA-001-{case_id}-{step_id}-{p_idx}",
                            rule_id="SEM-DATA-001",
                            severity="P1",
                            case_id=case_id,
                            branch_id=branch_id,
                            source_path=f"/steps/{section}/{s_idx}/parameters/{p_idx}/index_ref",
                            message=f"{source_type} parameter must have a non-empty index_ref",
                            expected="non-empty index_ref string",
                            actual=f"index_ref={index_ref!r}",
                            suggested_fix="add a valid index_ref pointing to the shared/public data source",
                            evidence_refs=[f"/steps/{section}/{s_idx}/parameters/{p_idx}"],
                        ))
    return issues


def _rule_parameter_atomization(sc: dict[str, Any], _ctx: dict[str, Any]) -> list[dict[str, Any]]:
    """Generated parameters must be atomic; no <br> aggregation in display_value.

    Each operation must independently generate parameter/data nodes.
    A display_value containing '<br>' indicates multiple facts merged into one.
    """
    issues: list[dict[str, Any]] = []
    case_id = sc.get("case_id", "unknown")
    branch_id = sc.get("branch_id")
    steps_obj = sc.get("steps", {})
    br_pattern = re.compile(r"<br\s*/?>", re.IGNORECASE)
    for section in ("setup", "feature", "assertions"):
        steps = steps_obj.get(section, []) if isinstance(steps_obj, dict) else []
        for s_idx, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            step_id = step.get("step_id", f"unknown-{section}-{s_idx}")
            parameters = step.get("parameters", [])
            if not isinstance(parameters, list):
                continue
            for p_idx, param in enumerate(parameters):
                if not isinstance(param, dict):
                    continue
                display_value = param.get("display_value", "")
                if not isinstance(display_value, str):
                    continue
                if br_pattern.search(display_value):
                    issues.append(_make_issue(
                        issue_id=f"SEM-ATOM-001-{case_id}-{step_id}-{p_idx}",
                        rule_id="SEM-ATOM-001",
                        severity="P1",
                        case_id=case_id,
                        branch_id=branch_id,
                        source_path=f"/steps/{section}/{s_idx}/parameters/{p_idx}/display_value",
                        message="parameter display_value contains <br> aggregation; each fact must be an independent parameter node",
                        expected="single atomic parameter per entry",
                        actual=f"display_value contains <br>: {display_value[:80]}",
                        suggested_fix="split the aggregated parameter into independent parameter entries",
                        evidence_refs=[f"/steps/{section}/{s_idx}/parameters/{p_idx}"],
                    ))
    return issues


# -- Registry --------------------------------------------------------------

RuleFn = Callable[[dict[str, Any], dict[str, Any]], list[dict[str, Any]]]

RULE_REGISTRY: list[tuple[str, RuleFn]] = [
    ("SEM-SCOPE-001", _rule_scope_consistency),
    ("SEM-DISPLAY-001", _rule_case_display_name),
    ("SEM-VARIANT-001", _rule_content_component_variant),
    ("SEM-ASSERT-001", _rule_assertion_target_mismatch),
    ("SEM-P0-001", _rule_p0_responsibility),
    ("SEM-R2-001", _rule_r2_ui_only_one_submit),
    ("SEM-DATA-001", _rule_shared_data_index_refs),
    ("SEM-ATOM-001", _rule_parameter_atomization),
]

RULE_IDS = [rule_id for rule_id, _ in RULE_REGISTRY]


def validate_semantics(source_case: dict[str, Any], *, source_path: str = "<inline>") -> list[dict[str, Any]]:
    """Run all semantic rules and return a stably sorted issue list.

    The list is sorted by (severity_order, case_id, branch_id, rule_id,
    source_path, issue_id) for deterministic output.
    """
    ctx: dict[str, Any] = {"source_path": source_path}
    raw: list[dict[str, Any]] = []
    for _rule_id, fn in RULE_REGISTRY:
        for issue in fn(source_case, ctx):
            # Override source_path base if not already path-like
            if not issue.get("source_path", "").startswith("/"):
                issue["source_path"] = source_path
            raw.append(issue)
    # Stable sort
    raw.sort(key=lambda i: (
        _SEVERITY_ORDER.get(i.get("severity", "info"), 99),
        i.get("case_id", ""),
        i.get("branch_id") or "",
        i.get("rule_id", ""),
        i.get("source_path", ""),
        i.get("issue_id", ""),
    ))
    return raw


def has_blocking_issues(issues: list[dict[str, Any]]) -> bool:
    """Return True if any issue is blocking (P0 or P1)."""
    return any(i.get("blocking") is True for i in issues)
