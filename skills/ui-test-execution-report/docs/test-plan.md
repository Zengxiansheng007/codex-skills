# Test Plan

## Deterministic Tests

| Test | Command | Expected |
|---|---|---|
| Skill structure validation | `python scripts/validate_execution_report_skill.py .` | zero P0/P1 |
| Sample report generation | `python scripts/generate_report.py --input assets/sample-run.json --output-root tmp/sample-output` | three artifacts generated |
| Generated output validation | `python scripts/validate_execution_report_skill.py . --generated-root tmp/sample-output` | six UI entries, four API JSON entries, attachment index, API index |

## Acceptance Mapping

| AC | Validation |
|---|---|
| AC-016 | Count `截图缩略图（点击放大）` markers in generated HTML |
| AC-017 | Count `点击查看 JSON` markers in generated HTML |
| AC-018 | Check Chapter 5 title and absence of old evidence-wall markers |
| AC-SKILL-001 | Check generated `report.html`, `evidence-index.json`, `execution-summary.json` |
| AC-SKILL-002 | Run validator and sensitive scan |
