# UI-Test 产品级总 Human View 开发计划 v1.1

## 1. 目标与边界

基于 `architecture-v1.1.md` 在候选 `candidate-skills/ui-test` 内完成显示名、产品/系统双节点、公共前置去重、特殊前置和漂移门禁。正式 D 盘发布、全局 Skill 修改、私有 UI 和业务写操作不在本轮自动执行。

## 2. Phase / Story

| Phase | Story | 目标 | 主要输出 | 完成标准 |
|---|---|---|---|---|
| PH-THV-01 | ST-THV-0101 | 固化需求与参考方案 | anchor、reference adaptation | 需求/参考来源可追溯 |
| PH-THV-02 | ST-THV-0201 | 扩展 Source Case/Case IR | schema、lowerer、semantic rules | display_name、precondition_group、special 前置可校验和 lowering |
| PH-THV-02 | ST-THV-0202 | 改造 Display Registry | config contract、registry adapter | 产品/系统/模块/功能显示名缺失 fail-closed |
| PH-THV-02 | ST-THV-0203 | 改造产品聚合 | product_aggregate、outline/manifest schema | 双层产品/系统、公共前置同级、中文用例名、参数原子节点 |
| PH-THV-03 | ST-THV-0301 | 完成漂移门禁 | stale/manual drift tests | 依赖变化先失效，重编译后才可 in_sync |
| PH-THV-03 | ST-THV-0302 | 完成候选验证 | pytest、compileall、scan、schema checks | 全量测试通过、敏感 0 命中 |
| PH-THV-04 | ST-THV-0401 | XMind Golden 与发布准备 | Golden evidence、publish manifest | Golden 通过后才可单独申请正式发布 |

## 3. 文件级任务

| 任务 | 文件 | 输入/接口 | 验证 |
|---|---|---|---|
| DEV-THV-001 | `schemas/source-case.schema.json` | Source Case contract | schema positive/negative |
| DEV-THV-002 | `schemas/case-ir.schema.json`、`case_contracts.py` | Source Case -> IR | lowering contract tests |
| DEV-THV-003 | `semantic_rules.py`、semantic tests | display_name facts | missing/Stable-ID/English name negative cases |
| DEV-THV-004 | `product_aggregate.py` | Display Registry + IR | outline tree and common Flow tests |
| DEV-THV-005 | `product-outline.schema.json`、`product-aggregate-manifest.schema.json` | new node types and labels | schema validation |
| DEV-THV-006 | `compiler.py` | special precondition section | standalone render tests |
| DEV-THV-007 | change records and RTM | all implementation evidence | lineage and sensitive scan |

## 4. 回滚与恢复

候选实现采用 workspace-copy-first。任一门禁失败，保留旧候选输出，标记 `repair-needed` 或 `blocked-external-dependency`，不激活正式输出。不得通过手改 Human View、outline 或 manifest 绕过 Source Case/依赖失效。

## 5. 依赖与发布门禁

继续复用已锁定的 `jsonschema`、`rfc8785` 和 pytest 运行时。新增依赖需要独立批准。XMind 桌面 Golden、依赖许可证和最终正式 D 盘写入均是后续独立门禁。
