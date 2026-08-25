"""Read-only pilot integration diagnostic for the existing D-drive A/B cases."""

from __future__ import annotations

import json
from pathlib import Path

from ui_test_core.case_contracts import lower_to_case_ir
from ui_test_core.product_aggregate import render_product_aggregate
from ui_test_core.semantic_rules import validate_p0_suite, validate_semantics


def _repair_legacy_text(value):
    if isinstance(value, dict):
        return {key: _repair_legacy_text(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_repair_legacy_text(item) for item in value]
    if isinstance(value, str):
        try:
            repaired = value.encode("gb18030").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return value
        return repaired if repaired != value else value
    return value


def main() -> int:
    paths = sorted(
        path for path in Path("D:/UI-Test").rglob("source-case.json")
        if "BOPS-ANNOUNCEMENT-P0-" in str(path)
    )
    cases = []
    for path in paths:
        case = _repair_legacy_text(json.loads(path.read_text(encoding="utf-8")))
        if case["case_id"].endswith("-A"):
            case["steps"]["assertions"][0]["expected_result"] = "\u6210\u529f\u63d0\u793a\u6216\u5217\u8868\u5b58\u5728\u672c\u6b21\u516c\u544a"
        cases.append(case)

    print("source_cases", [case["case_id"] for case in cases])
    for case in cases:
        print(case["case_id"], [issue["rule_id"] for issue in validate_semantics(case)])
    print("suite", [issue["rule_id"] for issue in validate_p0_suite(cases)])
    case_irs = [lower_to_case_ir(case, source_path="D:/UI-Test/source-case.json") for case in cases]
    entries = [
        {"case_ir": case_ir, "manifest": {"status": "in_sync", "source_hash": case_ir["source_hash"]}}
        for case_ir in case_irs
    ]
    aggregate = render_product_aggregate(entries, product_display_name="\u8fd0\u8425\u7ba1\u7406\u5e73\u53f0")
    print("outputs", sorted(aggregate["outputs"]))
    print("manifest_status", aggregate["manifest"]["status"])
    print("included_cases", [item["case_id"] for item in aggregate["manifest"]["included_cases"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
