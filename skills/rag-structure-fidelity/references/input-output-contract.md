# 输入输出契约

## 输入

- `md` 正文
- `doc/docx/pdf`
- `.lakebook` 目录对照
- 用户提供的首批材料清单

## 输出

- `structure_map.json`
- `evidence.json`
- `admission_report`
- `reject_report`
- `validation_report`

## 推荐字段

### structure_map.json
- `file_id`
- `block_id`
- `block_type`
- `parent_block_id`
- `source_ref`
- `recoverability`
- `criticality_candidate`
- `review_state`
- `blocked_reason`

### evidence.json
- `claim_id`
- `source_ref`
- `location_ref`
- `confidence`
- `candidate_only`
- `requires_human_confirmation`

## 边界

- 候选映射可以自动生成
- candidate 不能自动升级为 RC
- 正式下游交付必须经过 `rag-intake` 之后的治理确认

