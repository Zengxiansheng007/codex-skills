# Report Contract

## Required Input Shape

The generator accepts a UTF-8 JSON object:

```json
{
  "report": {},
  "run_result": {},
  "grouping": {},
  "safety": {},
  "steps": [],
  "attachments": [],
  "api_assertions": [],
  "failures": [],
  "midscene": {},
  "playwright": {},
  "score": {},
  "promotion": {}
}
```

## Required Fields

| Object | Field | Required |
|---|---|---|
| `report` | `report_id`, `run_id`, `case_id`, `case_name`, `status`, `started_at`, `ended_at`, `execution_date` | Yes |
| `run_result` | canonical `ui-test.run-result.v2`, including `run_result_hash` | Yes |
| `grouping` | `project_group`, `project`, `module`, `project_group_slug`, `project_slug`, `module_slug` | Yes |
| `steps[]` | `step_id`, `action`, `expected_result`, `actual_result`, `status` | Yes |
| `steps[].ui_evidence` | `attachment_id`, `path`, `captured_at`, `visible_state_summary`, `redaction_applied` | Required for UI-changing steps unless `missing_reason` exists |
| `steps[].api_assertion` | `api_assertion_id`, `method`, `url_template`, `http_status`, `assertion_status` | Required for API steps unless `missing_reason` exists |

## HTML Layout Contract

`report.html` must render the step table as the human evidence source of truth:

| Column | Behavior |
|---|---|
| `UI 图片` | Shows thumbnail in the table cell. Expands to a larger image, screenshot path, and screenshot evidence JSON. |
| `接口断言` | Shows API/assertion ID in the table cell. Expands to redacted JSON details, request/response summary, JSONPath assertions, and raw JSON path. |

Chapter 5 is an attachment index only. Chapter 6 is an API summary index only.

Status governance:

- The generator consumes canonical RunResult v2 and never recalculates pass/fail from report steps.
- `report.status`, execution summary, evidence index and copied `run-result.json` must preserve the canonical result identity and hash.
- Legacy report input without RunResult v2 is migration-only and must fail closed.

## Output Layout

```text
<output-root>/
  human-html/<project_group_slug>/<project_slug>/<module_slug>/<YYYY-MM-DD>/<run_id>/report.html
  agent-readable/<project_group_slug>/<project_slug>/<module_slug>/<YYYY-MM-DD>/<run_id>/evidence-index.json
  agent-readable/<project_group_slug>/<project_slug>/<module_slug>/<YYYY-MM-DD>/<run_id>/execution-summary.json
```

Directory governance:

- Path segments must be filesystem-safe.
- Long `run_id` values may be shortened in the directory name with a stable hash suffix.
- The original `run_id` must remain unchanged inside `report.html`, `evidence-index.json`, and `execution-summary.json`.
- Generators should keep each path segment under 80 characters to avoid Windows path-length failures in nested report centers.

## Redaction Rules

The generator must fail on obvious sensitive key names or values:

- `password`
- `passwd`
- `authorization`
- `cookie`
- `set-cookie`
- `token`
- `secret`
- `api_key`
- `x-token`

Allowed examples may include these terms only in policy text or redaction summaries, not as live values.
