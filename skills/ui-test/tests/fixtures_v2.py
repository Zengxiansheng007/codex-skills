"""Synthetic, project-neutral fixtures for v2 governance tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from scripts.ui_test_core.compiler_v2 import compile_case_v2
from scripts.ui_test_core.test_data_contracts import load_test_data


def source_case_v2() -> dict[str, Any]:
    return {
        "schema_version": "ui-test.source-case.v2",
        "case_id": "DEMO-CASE-A",
        "branch_id": "primary",
        "case_version": 2,
        "title": "创建示例记录",
        "display_name": "创建示例记录核心冒烟",
        "priority": "P0",
        "risk_level": "R2",
        "scope": {"project_group": "demo", "product": "sample-product", "function": "create"},
        "parameter_bindings": [
            {"parameter_id": "title-template", "label": "标题规则", "ref": "test-data:/parameters/title_template"},
            {"parameter_id": "content-template", "label": "内容规则", "ref": "test-data:/parameters/content_template"},
            {"parameter_id": "audiences", "label": "受众", "ref": "test-data:/parameters/audiences"},
            {"parameter_id": "date-offset", "label": "日期偏移", "ref": "test-data:/generation_rules/expiry_offset_days"},
            {"parameter_id": "time-suffix-digits", "label": "时间后缀位数", "ref": "test-data:/generation_rules/time_suffix_digits"},
            {"parameter_id": "service-host", "label": "服务地址", "ref": "value:SERVICE_HOST"},
            {"parameter_id": "login-account", "label": "测试账号", "ref": "credential:shared-login"},
            {"parameter_id": "version", "label": "版本号", "ref": "sequence:popup-version"}
        ],
        "steps": [
            {"step_id": "S-001", "section": "setup", "intent": "进入创建页", "action": "flow", "parameter_ids": ["service-host", "login-account"], "expected_result": "创建页可见", "binding_ref": "flow.open-create", "evidence": ["page-ready"]},
            {"step_id": "S-002", "section": "feature", "intent": "填写业务字段", "action": "fill", "parameter_ids": ["title-template", "content-template", "audiences", "date-offset", "time-suffix-digits", "version"], "expected_result": "全部字段已填写", "binding_ref": "component.form.fill", "evidence": ["form-state"]},
            {"step_id": "S-003", "section": "assertions", "intent": "核对字段", "action": "assert", "parameter_ids": ["title-template", "audiences"], "expected_result": "字段值正确", "binding_ref": "component.form.assert", "evidence": ["field-values"]}
        ],
        "dependency_refs": ["flow.open-create", "component.form.fill", "component.form.assert"],
        "p0_suite_id": "DEMO-P0"
    }


def make_test_data_document() -> dict[str, Any]:
    return {
        "schema_version": "ui-test.test-data.v2",
        "case_id": "DEMO-CASE-A",
        "branch_id": "primary",
        "data_revision": 1,
        "parameters": {
            "title_template": "{date_mmdd}{time_suffix}{record_type}",
            "content_template": "自动化测试-{title}",
            "audiences": ["个人", "法人"]
        },
        "generation_rules": {"expiry_offset_days": 1, "time_suffix_digits": 3},
        "runtime_refs": ["value:SERVICE_HOST", "credential:shared-login", "sequence:popup-version"],
        "metadata": {"owner": "qa", "manually_editable": True}
    }


def write_test_data(path: Path, document: dict[str, Any] | None = None) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document or make_test_data_document(), ensure_ascii=False, indent=2), encoding="utf-8")
    return load_test_data(path, case_id="DEMO-CASE-A", branch_id="primary")


def compiled_v2(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    loaded = write_test_data(path)
    source = source_case_v2()
    compiled = compile_case_v2(
        source_case=source,
        test_data=loaded,
        dependency_assets={
            "flow.open-create": {"version": 1, "steps": ["login", "navigate"]},
            "component.form.fill": {"version": 1, "operation": "fill"},
            "component.form.assert": {"version": 1, "operation": "assert"}
        },
        config_fingerprint="sha256:" + "1" * 64,
        runtime_values={"SERVICE_HOST": {"value": "sample.internal", "classification": "ordinary", "sensitive": False}},
        credential_keys={"shared-login"},
        sequence_keys={"popup-version"}
    )
    return compiled, copy.deepcopy(loaded)
