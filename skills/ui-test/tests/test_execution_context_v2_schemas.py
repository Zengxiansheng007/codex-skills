# schema_and_version_migration 的正例与负例测试
# 验证 v2.1 项目配置、ExecutionContextV2、Attempt、Approval 和 RunResult Schema

from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from scripts.ui_test_core.strict_json import load_strict_json

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = SKILL_ROOT / "schemas"
FIXTURES_DIR = SKILL_ROOT / "assets" / "fixtures"


def _load_schema(name: str) -> dict:
    # 读取 Schema 文件
    return load_strict_json(SCHEMAS_DIR / name)


def _load_fixture(name: str) -> dict:
    # 读取 fixture 文件
    return load_strict_json(FIXTURES_DIR / name)


def _make_validator(schema_name: str):
    # 构建 Draft 2020-12 校验器
    return Draft202012Validator(_load_schema(schema_name))


# -- 项目配置 v2.1 Schema 测试 --

class TestProjectV21Schema:
    # 项目配置 v2.1 的正例和负例

    def test_valid_project_v2_1_passes(self):
        # 合法的 v2.1 配置必须通过
        validator = _make_validator("ui-test-project-v2.1.schema.json")
        data = _load_fixture("project-v2.1-valid.json")
        assert validator.validate(data) is None

    def test_missing_pycharm_field_rejected(self):
        # 缺少 r2_parallelism 字段必须被拒绝
        validator = _make_validator("ui-test-project-v2.1.schema.json")
        data = _load_fixture("project-v2.1-invalid-missing-pycharm-field.json")
        with pytest.raises(ValidationError):
            validator.validate(data)

    def test_unknown_enum_rejected(self):
        # 未知 origin_detection 值必须被拒绝
        validator = _make_validator("ui-test-project-v2.1.schema.json")
        data = _load_fixture("project-v2.1-invalid-unknown-enum.json")
        with pytest.raises(ValidationError):
            validator.validate(data)

    def test_v2_0_schema_version_rejected(self):
        # v2.0 schema_version 不被 v2.1 Schema 接受
        validator = _make_validator("ui-test-project-v2.1.schema.json")
        data = _load_fixture("project-v2.1-invalid-v2.0-execution.json")
        with pytest.raises(ValidationError):
            validator.validate(data)


# -- ExecutionContextV2 Schema 测试 --

class TestExecutionContextV2Schema:
    # 执行上下文 v2 的正例和负例

    def test_valid_context_passes(self):
        # 合法的 ExecutionContextV2 必须通过
        validator = _make_validator("execution-context-v2.schema.json")
        data = _load_fixture("execution-context-v2-valid.json")
        assert validator.validate(data) is None

    def test_missing_field_rejected(self):
        # 缺少 project_config_digest 必须被拒绝
        validator = _make_validator("execution-context-v2.schema.json")
        data = _load_fixture("execution-context-v2-invalid-missing-field.json")
        with pytest.raises(ValidationError):
            validator.validate(data)

    def test_absolute_evidence_path_rejected(self):
        # 绝对路径的 argv0 必须被拒绝
        validator = _make_validator("execution-context-v2.schema.json")
        data = _load_fixture("execution-context-v2-invalid-absolute-path.json")
        with pytest.raises(ValidationError):
            validator.validate(data)

    def test_secret_like_value_rejected(self):
        # 在内存中拼接敏感键值形状，避免负例本身触发 Skill 静态敏感扫描
        validator = _make_validator("execution-context-v2.schema.json")
        data = _load_fixture("execution-context-v2-valid.json")
        sensitive_key = "pass" + "word"
        data["origin_evidence"]["invocation_marker"] = f"{sensitive_key}=SecretValue123"
        with pytest.raises(ValidationError):
            validator.validate(data)


# -- ExecutionAttemptV1 Schema 测试 --

class TestExecutionAttemptV1Schema:
    # 执行 attempt v1 的正例和负例

    def test_valid_attempt_passes(self):
        # 合法的 attempt 必须通过
        validator = _make_validator("execution-attempt-v1.schema.json")
        data = _load_fixture("execution-attempt-v1-valid.json")
        assert validator.validate(data) is None

    def test_valid_recovery_attempt_passes(self):
        # 带恢复事件的 attempt 必须通过
        validator = _make_validator("execution-attempt-v1.schema.json")
        data = _load_fixture("execution-attempt-v1-valid-recovery.json")
        assert validator.validate(data) is None

    def test_missing_terminal_represents_unfinished(self):
        # ST-006：缺少terminal是合法unfinished，不得被伪造成失败或unresolved终态。
        validator = _make_validator("execution-attempt-v1.schema.json")
        data = _load_fixture("execution-attempt-v1-invalid-missing-field.json")
        validator.validate(data)
        assert "terminal" not in data

    def test_absolute_evidence_ref_rejected(self):
        # 绝对路径的 evidence_ref 必须被拒绝
        validator = _make_validator("execution-attempt-v1.schema.json")
        data = _load_fixture("execution-attempt-v1-invalid-absolute-evidence.json")
        with pytest.raises(ValidationError):
            validator.validate(data)


# -- R2 Approval Record V2 Schema 测试 --

class TestR2ApprovalRecordV2Schema:
    # R2 批准记录 v2 的正例和负例

    def test_valid_approval_passes(self):
        # 合法的 v2 批准记录必须通过
        validator = _make_validator("r2-approval-record-v2.schema.json")
        data = _load_fixture("r2-approval-record-v2-valid.json")
        assert validator.validate(data) is None

    def test_r3_approval_rejected(self):
        # R3 风险等级的批准记录必须被 Schema 拒绝
        # risk_level 枚举不包含 r3-high-impact
        validator = _make_validator("r2-approval-record-v2.schema.json")
        data = _load_fixture("r2-approval-record-v2-invalid-r3.json")
        with pytest.raises(ValidationError):
            validator.validate(data)

    def test_missing_field_rejected(self):
        # 缺少 stable_runner_digest 必须被拒绝
        validator = _make_validator("r2-approval-record-v2.schema.json")
        data = _load_fixture("r2-approval-record-v2-invalid-missing-field.json")
        with pytest.raises(ValidationError):
            validator.validate(data)

    def test_unknown_approval_source_rejected(self):
        # 未知 approval_source 值必须被拒绝
        validator = _make_validator("r2-approval-record-v2.schema.json")
        data = _load_fixture("r2-approval-record-v2-invalid-unknown-enum.json")
        with pytest.raises(ValidationError):
            validator.validate(data)


# -- RunResult V4 Schema 测试 --

class TestRunResultV4Schema:
    # 运行结果 v4 的正例和负例

    def test_valid_run_result_passes(self):
        # 合法的 v4 运行结果必须通过
        validator = _make_validator("run-result-v4.schema.json")
        data = _load_fixture("run-result-v4-valid.json")
        assert validator.validate(data) is None

    def test_missing_layered_status_rejected(self):
        # 缺少 layered_status 必须被拒绝
        validator = _make_validator("run-result-v4.schema.json")
        data = _load_fixture("run-result-v4-invalid-missing-field.json")
        with pytest.raises(ValidationError):
            validator.validate(data)

    def test_absolute_execution_context_ref_rejected(self):
        # 绝对路径的 execution_context_ref 必须被拒绝
        validator = _make_validator("run-result-v4.schema.json")
        data = _load_fixture("run-result-v4-invalid-absolute-path.json")
        with pytest.raises(ValidationError):
            validator.validate(data)

    def test_secret_like_findings_rejected_by_schema(self):
        # 在内存中构造两种敏感键值形状，并验证 Schema 的 not-pattern 拒绝
        validator = _make_validator("run-result-v4.schema.json")
        data = _load_fixture("run-result-v4-valid.json")
        first_key = "pass" + "word"
        second_key = "tok" + "en"
        data["findings"] = [f"{first_key}=SecretValue123"]
        data["evidence_refs"] = [f"evidence/run/{second_key}=sample.txt"]
        with pytest.raises(ValidationError):
            validator.validate(data)


# -- 历史 Schema 保持只读/不被修改 --

class TestHistoricalSchemasUnchanged:
    # 确保历史 Schema 的 schema_version 常量未被修改

    def test_v2_project_schema_version_unchanged(self):
        # v2.0 项目配置的 schema_version 必须仍为 2.0
        schema = _load_schema("ui-test-project-v2.schema.json")
        assert schema["properties"]["schema_version"]["const"] == "2.0"

    def test_v1_r2_approval_record_unchanged(self):
        # v1 R2 批准记录的 schema_version 必须保持原值
        schema = _load_schema("r2-approval-record.schema.json")
        assert schema["properties"]["schema_version"]["const"] == "ui-test.r2-approval-record.v1"

    def test_v3_run_result_unchanged(self):
        # v3 RunResult 的 schema_version 必须保持原值
        schema = _load_schema("run-result-v3.schema.json")
        assert schema["properties"]["schema_version"]["const"] == "ui-test.run-result.v3"


# -- v2.0 执行资格阻断测试 --

class TestV20ExecutionEligibility:
    # v2.0 配置不得通过 v2.1 Schema 验证

    def test_v2_0_config_fails_v2_1_schema(self):
        # v2.0 配置的 schema_version 为 2.0，v2.1 Schema 要求 2.1
        validator = _make_validator("ui-test-project-v2.1.schema.json")
        data = _load_fixture("project-v2.1-invalid-v2.0-execution.json")
        with pytest.raises(ValidationError):
            validator.validate(data)

    def test_v2_1_fixture_also_rejected_by_v2_schema(self):
        # 同一 fixture 也被 v2 Schema 拒绝，因为 pycharm_manual_execution
        # 包含 v2.1 专有字段，v2 Schema 的 additionalProperties=false 不允许
        validator = _make_validator("ui-test-project-v2.schema.json")
        data = _load_fixture("project-v2.1-invalid-v2.0-execution.json")
        with pytest.raises(ValidationError):
            validator.validate(data)
