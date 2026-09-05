# CR-20260825-005：Display Name、产品/系统双层与公共前置聚合

Status: implemented-candidate

## Summary

候选实现已增加产品级总用例的中文显示名、产品/系统双层节点、公共 Flow 去重和特殊前置投影。

## Context And Problem

旧聚合器使用 Stable ID 作为主标签，并把 setup 重复放到每条用例下，无法满足 XMind 治理层级和公共前置复用要求。

## Sections Changed

## 变更类型

- 类型：候选实现升级
- 需求锚点：`RA-UI-TEST-TOTAL-HUMAN-VIEW-20260825-v1.1`
- 范围：当前候选 `ui-test` 工作区
- 不包含：D 盘正式发布、D 盘 RAG 写入、全局 Skill、私有 UI、业务写操作

## 变更内容

- Source Case 增加 `display_name`、`precondition_group`、`special_preconditions` 契约。
- Case IR 保留显示名和公共前置组，并将特殊前置投影为独立 section。
- 产品聚合从 Display Registry 读取项目组、产品、系统、模块、功能显示名。
- Human View/XMind 保留项目组 -> 产品 -> 系统双层；产品与系统同名不去重。
- 同一功能同一公共 Flow 组只渲染一份公共前置操作。
- 单用例 compiler 仍保留完整 setup，保证每个 Playwright 用例独立执行。
- 增加显示名语义门禁、同组公共前置冲突门禁和对应测试夹具。

## 验证

`python -m pytest -q`：134 passed。

## Decision And Alternatives

采用现有 Case IR 管线和 Display Registry 适配，不引入第二套 testcase runtime；同名产品/系统保留双节点，不做去重。

## Impact Analysis

Source Case 和 Case IR schema 增加显示名、公共前置组和特殊前置字段；单用例编译仍保留完整 setup，产品聚合视图只做展示去重。

## Validation Evidence

- `python -m pytest -q`：134 passed。
- `python -m compileall -q scripts tests`：passed。
- JSON Schema 解析：passed。
- 敏感扫描：0 findings。

## Safety And Privacy

仅使用候选工作区和合成 fixture；未读取或写入凭据、私有页面、D 盘正式资产、D 盘 RAG 或全局 Skill。

## 回滚

在候选工作区恢复本变更前的 `product_aggregate.py`、Source Case/Case IR schema、`case_contracts.py`、`compiler.py` 和相关测试；不触碰正式 D 盘资产。

## Risks And Follow-up

XMind 桌面 Golden 和正式 D 盘发布仍待独立门禁；候选包历史 change records 仍有既有格式告警，不在本次业务实现中重写。
| Status | validated |
