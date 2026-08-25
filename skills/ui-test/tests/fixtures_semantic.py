"""Synthetic Source Case fixtures for ST-TOTAL-0402 semantic validation tests.

All fixtures are synthetic and use public/synthetic data only.
No credentials, cookies, tokens, or private URLs are present.
"""

from __future__ import annotations

import copy
from typing import Any


def _base_a_plain() -> dict[str, Any]:
    """Branch A (system-announcement) with correct plain-content component."""
    return {
        "schema_version": "ui-test.source-case.v1",
        "case_id": "FIXTURE-A-PLAIN-001",
        "case_version": 1,
        "title": "Create system announcement (A, plain text)",
        "display_name": "创建系统公告核心冒烟",
        "status": "approved",
        "priority": "P0",
        "p0_suite_id": "FIXTURE-ANNOUNCEMENT-P0",
        "branch_id": "system-announcement",
        "scope": {
            "project_group": "test-group",
            "product": "test-platform",
            "product_aliases": ["tp"],
            "system": "test-config",
            "module_path": ["message", "announcement"],
            "function": "create",
        },
        "risk": {
            "risk_level": "R2",
            "write_action": "create-announcement",
            "max_submit_count": 1,
            "environment_allowlist": ["test"],
            "ui_only": True,
            "forbidden_actions": ["api-create", "production"],
        },
        "precondition_group": "announcement-create-common",
        "precondition_flow_refs": [{"id": "flow.login-and-open-create", "version": 1}],
        "special_preconditions": [],
        "page_object_refs": [{"id": "page.announcement-create", "version": 1}],
        "component_refs": [{"id": "component.plain-content", "version": 1}],
        "test_points": [
            {
                "test_point_id": "announcement-content/plain",
                "responsibility": "primary",
                "coverage_method": "operation",
                "variant": "plain-text",
                "assertion_refs": ["A-CONTENT"],
            }
        ],
        "steps": {
            "setup": [
                {
                    "step_id": "S-LOGIN",
                    "intent": "reach create page",
                    "action": "flow",
                    "binding_ref": "flow.login-and-open-create",
                    "parameters": [
                        {
                            "label": "test account",
                            "display_value": "shared_account.test_user",
                            "source_type": "shared-data",
                            "index_ref": "test-index.yaml#shared_account.test_user",
                            "sensitive": True,
                        }
                    ],
                    "expected_result": "create page ready",
                    "risk_level": "R1",
                    "required": True,
                    "evidence": ["screenshot"],
                    "forbidden_actions": [],
                }
            ],
            "feature": [
                {
                    "step_id": "S-FILL",
                    "intent": "fill content",
                    "action": "fill",
                    "binding_ref": "component.plain-content.fill",
                    "parameters": [
                        {"label": "content", "display_value": "sample text", "source_type": "literal", "sensitive": False}
                    ],
                    "expected_result": "content visible",
                    "risk_level": "R1",
                    "required": True,
                    "evidence": ["field-state"],
                    "forbidden_actions": [],
                }
            ],
            "assertions": [
                {
                    "step_id": "S-ASSERT",
                    "intent": "verify content",
                    "action": "assert",
                    "binding_ref": "component.plain-content.assert",
                    "expected_result": "plain content matches",
                    "risk_level": "R1",
                    "required": True,
                    "evidence": ["field-state"],
                    "forbidden_actions": [],
                }
            ],
        },
        "data_rules": {"expiry_offset_days": 1},
        "generation": {"human": True, "midscene": True, "resolved": True, "playwright": True},
        "source_refs": ["REQ-FIXTURE-A"],
    }


def _base_b_rich() -> dict[str, Any]:
    """Branch B (homepage-popup) with correct rich-content component."""
    base = _base_a_plain()
    base["case_id"] = "FIXTURE-B-RICH-001"
    base["title"] = "Create homepage popup (B, rich text)"
    base["display_name"] = "创建首页弹窗公告核心冒烟"
    base["branch_id"] = "homepage-popup"
    base["component_refs"] = [{"id": "component.rich-content", "version": 1}]
    base["test_points"] = [
        {
            "test_point_id": "popup-content/rich",
            "responsibility": "primary",
            "coverage_method": "operation",
            "variant": "rich-text",
            "assertion_refs": ["B-CONTENT"],
        }
    ]
    base["steps"]["feature"][0]["binding_ref"] = "component.rich-content.fill"
    base["steps"]["assertions"][0]["binding_ref"] = "component.rich-content.assert"
    base["steps"]["assertions"][0]["expected_result"] = "rich content matches"
    base["steps"]["assertions"][0]["intent"] = "verify rich content"
    return base


# -- Positive fixtures -----------------------------------------------------

def fixture_a_plain_valid() -> dict[str, Any]:
    """A with plain-content component — should pass all semantic rules."""
    return _base_a_plain()


def fixture_b_rich_valid() -> dict[str, Any]:
    """B with rich-content component — should pass all semantic rules."""
    return _base_b_rich()


# -- Negative fixtures -----------------------------------------------------

def fixture_a_rich_content_component() -> dict[str, Any]:
    """A with rich-content component — should be blocked (variant mismatch)."""
    sc = _base_a_plain()
    sc["component_refs"] = [{"id": "component.rich-content", "version": 1}]
    sc["test_points"][0]["variant"] = "rich-text"
    return sc


def fixture_a_popup_version_assertion() -> dict[str, Any]:
    """A asserting popup-version — should be blocked (assertion mismatch)."""
    sc = _base_a_plain()
    sc["steps"]["assertions"][0]["expected_result"] = "popup version visible"
    sc["steps"]["assertions"][0]["intent"] = "verify popup version"
    return sc


def fixture_b_plain_content_component() -> dict[str, Any]:
    """B with plain-content component — should be blocked (variant mismatch)."""
    sc = _base_b_rich()
    sc["component_refs"] = [{"id": "component.plain-content", "version": 1}]
    sc["test_points"][0]["variant"] = "plain-text"
    sc["steps"]["feature"][0]["binding_ref"] = "component.plain-content.fill"
    sc["steps"]["assertions"][0]["binding_ref"] = "component.plain-content.assert"
    sc["steps"]["assertions"][0]["expected_result"] = "plain content matches"
    sc["steps"]["assertions"][0]["intent"] = "verify content"
    return sc


def fixture_missing_p0_responsibility() -> dict[str, Any]:
    """P0 case with no primary responsibility test_point — should be blocked."""
    sc = _base_a_plain()
    sc["test_points"][0]["responsibility"] = "supporting"
    return sc


def fixture_missing_shared_data_index_ref() -> dict[str, Any]:
    """shared-data parameter without index_ref — should be blocked."""
    sc = _base_a_plain()
    sc["steps"]["setup"][0]["parameters"][0].pop("index_ref")
    return sc


def fixture_br_parameter_aggregation() -> dict[str, Any]:
    """Parameter display_value containing <br> — should be blocked."""
    sc = _base_a_plain()
    sc["steps"]["feature"][0]["parameters"][0]["display_value"] = "line1<br>line2"
    return sc


def fixture_r2_multi_submit() -> dict[str, Any]:
    """R2 with max_submit_count=2 — should be blocked."""
    sc = _base_a_plain()
    sc["risk"]["max_submit_count"] = 2
    return sc
