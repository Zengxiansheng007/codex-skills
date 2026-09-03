import copy

import pytest

from scripts.ui_test_core.case_contracts import validate_document
from scripts.ui_test_core.product_aggregate import AggregateError, render_product_aggregate_v2
from tests.fixtures_v2 import compiled_v2


def _registry():
    return {
        "project_groups": {"demo": "示例项目组"},
        "products": {"sample-product": "示例产品"},
        "systems": {"sample-system": "示例系统"},
        "modules": {"records": "记录管理"},
        "functions": {"create": "创建"},
    }


def _entry(compiled):
    return {
        "case_ir": compiled["case_ir"],
        "resolved_ir": compiled["resolved_ir"],
        "manifest": compiled["manifest"],
        "release_state": {"release_integrity": "valid", "input_sync": "in_sync", "execution_gate": "ready"},
    }


def test_v2_aggregate_restores_hierarchy_and_atomic_nodes(tmp_path):
    compiled, _ = compiled_v2(tmp_path / "test-data.json")
    result = render_product_aggregate_v2([_entry(compiled)], display_registry=_registry(), config_fingerprint="sha256:" + "1" * 64)
    markdown = result["outputs"]["示例产品.总测试用例.md"]
    assert markdown.startswith("# 示例项目组\n")
    assert "- 示例产品\n  - 示例系统" in markdown
    assert "公共前置操作" in markdown
    assert "P0-创建示例记录核心冒烟" in markdown
    assert "参数/数据" in markdown and "预期：" in markdown
    assert "<br>" not in markdown
    assert validate_document(result["outline"], "product-outline-v2.schema.json") == []
    assert validate_document(result["manifest"], "product-aggregate-manifest-v2.schema.json") == []


def test_v2_aggregate_rejects_non_ready_case(tmp_path):
    compiled, _ = compiled_v2(tmp_path / "test-data.json")
    entry = _entry(compiled)
    entry["release_state"]["input_sync"] = "out_of_sync"
    with pytest.raises(AggregateError, match="E_AGGREGATE_CASE_NOT_IN_SYNC"):
        render_product_aggregate_v2([entry], display_registry=_registry(), config_fingerprint="sha256:" + "1" * 64)


def test_v2_aggregate_rejects_source_hash_drift(tmp_path):
    compiled, _ = compiled_v2(tmp_path / "test-data.json")
    entry = copy.deepcopy(_entry(compiled))
    entry["resolved_ir"]["source_hash"] = "sha256:" + "0" * 64
    with pytest.raises(AggregateError, match="E_AGGREGATE_SOURCE_HASH_MISMATCH"):
        render_product_aggregate_v2([entry], display_registry=_registry(), config_fingerprint="sha256:" + "1" * 64)
