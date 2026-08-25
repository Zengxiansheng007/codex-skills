# CR-20260825-006：正式资产发布与全局 Skill 部署

| Field | Value |
|---|---|
| Status | validated |
| Target Skill | ui-test |
| Change Type | formal-publish / global-deployment / validation |
| Scope | Tianjin announcement pilot, product aggregate, global Skill |
| Source | RA-UI-TEST-TOTAL-HUMAN-VIEW-20260825-v1.1 |
| Baseline | CR-20260825-005 |
| Author | Codex |

## Summary

将产品级总 Human View、A/B 公告 Source Case 派生物和项目配置按 v1.1 规则发布到 `D:\UI-Test`，并将同一候选 Skill 部署到全局 `ui-test` Skill 目录。

## Context And Problem

候选实现已经通过本地测试，但正式 D 盘资产仍缺少新版 Source Case 字段，产品聚合物仍使用旧显示名；全局 Skill 也尚未包含本轮语义校验、产品聚合和命名修复。

## Sections Changed

- 项目组：天津项目组
- 产品显示名：运维管理系统
- 系统显示名：运维管理系统
- 功能范围：运营配置 / 消息管理 / 公告管理 / 创建
- 用例：`BOPS-ANNOUNCEMENT-P0-A`、`BOPS-ANNOUNCEMENT-P0-B`
- 允许的写入根：`D:\UI-Test`、`D:\RAG`、全局 `C:\Users\lenovo\.codex\skills\ui-test`

## Changes

- 补齐 A/B 的 `display_name`、`precondition_group` 和 `special_preconditions`。
- 修正 A 的错误断言，不再声称弹窗公告版本为最新。
- 将项目配置的产品和系统显示名统一为“运维管理系统”。
- 产品聚合器统一生成：
  - `运维管理系统.总测试用例.md`
  - `运维管理系统.总测试用例.outline.json`
  - `运维管理系统.总测试用例.manifest.json`
- 旧“运营管理平台”总用例移入 D 盘 `_tmp` superseded 区，保留可回滚记录。
- 全局 Skill 更新前创建完整备份和 hash 清单；部署后重新执行验证。

## Decision And Alternatives

- 采用候选 Skill 作为唯一全局实现，与正式 D 盘资产使用同一编译器和 Schema。
- 保留稳定英文 ID 和现有正式目录根，不重命名稳定目录；仅更新受治理的显示名和总用例文件名。
- 旧总用例移入可回滚 `_tmp` superseded 区，不与新总用例并存于正式产品根目录。

## Impact Analysis

- A/B Source Case、Case IR、Human View、Midscene View、Resolved Case、Playwright Test、manifest 和 compile receipt 的 hash/lineage 重新计算。
- 产品总用例改为产品显示名驱动，并保留产品/系统两个同名节点。
- 项目配置产品/系统显示名变更会使下游派生物重新同步。
- 全局 `ui-test` 增加产品聚合输出命名、语义规则和正式发布验证能力。

## Validation Evidence

- Formal backup: `D:\UI-Test\_tmp\formal-publish-backup-20260825-total-human-view-v1.1-r3`
- Superseded aggregate: `D:\UI-Test\_tmp\superseded-product-aggregate-20260825-v1.1-r3`
- Candidate pytest: `134 passed`
- Formal publish verification: `passed`
- Candidate sensitive scan: `0 findings`
- XMind Golden import: user-confirmed format correct

- Candidate validator: accepted-with-constraints, P0=0, P1=0, P2=0
- Candidate pytest: 134 passed
- Formal publish verification: passed
- Candidate compileall: passed
- Candidate sensitive scan: clear, 0 findings

## Safety And Privacy

- 未执行私有 UI 测试或业务写操作。
- 未持久化账号、密码、Cookie、Token 或 storage state。
- 共享账号只保留环境变量索引引用。

## Risks And Follow-up

- 私有 UI 真实执行不属于本次发布，仍需按独立授权和测试环境门禁执行。
- D 盘当前仍保留历史运行证据和未归档尝试批次，均位于 `_tmp`，后续按迁移任务单治理。
- 全局 Skill 部署后必须再次执行全局 validator 和单测。

## Rollback

按 backup manifest 将本次发布涉及的 Source Case、派生物、项目配置和旧总用例恢复；全局 Skill 使用同批次 global backup 回滚。
