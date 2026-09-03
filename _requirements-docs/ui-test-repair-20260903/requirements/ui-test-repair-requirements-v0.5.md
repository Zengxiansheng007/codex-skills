# UI-Test 参数、同步、迁移与失败修复治理需求

状态：`approved / 已批准`  
规范 Envelope：`envelopes/prd-v0.5.envelope.json`  
需求锚点：`RA-UI-TEST-REPAIR-20260830@v0.7`  
说明：旧版本保持只读；本文件是当前后继版本，不回写历史文档。

## 1. 背景与问题

天津运营管理平台公告创建 A/B 用例当前存在以下治理问题：

- 公告业务数据同时存在于 Source Case 规则和 Python 运行代码中，缺乏唯一可人工修改来源；
- Compiler、manifest、receipt、Human/Midscene/Resolved/Playwright 未贯穿同一参数身份；
- manifest-driven verifier 曾因固定附件子集产生误报；
- 参数文件变化后，旧 active release 和执行入口缺少统一 `out_of_sync` 门禁；
- 失败、待修复项、修复历史和清理处置缺少产品级统一记录；
- 旧格式资产不满足新治理要求，不能直接继续执行；
- 全局 Skill 内存在天津专属治理脚本，通用能力与项目适配未完全隔离。

截至 2026-09-02，`<formal-root>` 正式业务树只有天津公告创建 A/B 两个用例及直接依赖；正式产品树共有 402 个文件。当前没有分支级 `test-data.json`，产品级 diagnostics 目录尚未建立。

## 2. 目标

### GOAL-001 唯一业务数据来源

测试工程师只修改分支级 `tests\test-data.json` 即可治理稳定业务参数和生成规则；Source Case 只拥有测试意图、步骤、断言和字段语义。

### GOAL-002 确定性编译、同步与执行

Source Case、Test Data、受引用 Runtime、依赖和配置共同形成可验证构建身份；编译、同步和执行均可检测漂移并 fail closed。

### GOAL-003 可追溯失败、修复和运行数据

所有失败层摘要、待修复项、修复事件和实际运行参数均可按用例、分支、问题指纹、build、data revision 和 run_id 追溯。

### GOAL-004 完成现存正式资产迁移和非正式资产治理

开发交付必须同步完成 A/B 当前正式资产及直接依赖的受控迁移；历史资产保持不可变，临时、备份、缓存和 IDE 资产进入分类清理治理。

### GOAL-005 保持安全、作用域和授权边界

通用引擎不包含天津业务常量；凭据不进入禁止输出；开发完成不自动授权全局部署、正式迁移、删除或真实 UI/R2。

## 3. 角色与权限

| 角色 | 权限与责任 |
|---|---|
| 测试工程师 | 人工修改分支 `test-data.json`，查看 Human/Playwright 参数投影和 diagnostics；不能手工修改派生物。 |
| Codex 控制面 | 需求追踪、架构与 Phase 划分、计划生成、风险门禁、证据评审和完成判定。 |
| 固定脚本执行面 | 确定性校验、编译、dry-run/apply、验证、日志和迁移；不能自行扩大授权。 |
| 全局 ui-test 通用引擎 | 通用 Schema、哈希、编译、同步、Guard、日志、验证和迁移框架。 |
| 天津项目适配器 | 天津路径、A/B case/branch 映射、公告字段绑定、页面定位器和产品 diagnostics 路径。 |

## 4. 术语与事实源

| 术语 | 定义 |
|---|---|
| Source Case 事实域 | 测试意图、步骤、断言、字段语义、风险和依赖引用的权威来源。 |
| Test Data 事实域 | 稳定业务参数值与生成规则的唯一可编辑来源。 |
| Runtime Value | 环境相关、非凭据运行值；只有显式 `sensitive=false` 才允许编译展开。 |
| Credential | 平台级账号密码；只存在于私有索引和受控进程内存。 |
| Runtime State | 跨运行递增序列及其分配记录；当前值不属于 Test Data。 |
| Build Identity | Source、Test Data、被引用且参与构建的 Runtime、依赖、Schema、编译器、renderer 和配置身份的组合。 |
| Release Integrity | 不可变 release 内部附件、manifest、receipt 与哈希是否一致。 |
| Input Sync | 当前 Source/Test Data/Runtime/依赖与 active build 是否一致。 |
| Execution Eligibility | 资产完成迁移、验证且当前门禁通过后，具备申请真实执行的资格。 |
| Historical Asset | 已发布 release、既有 run、RunResult、报告、证据和审计记录；不可原位改写。 |

## 5. 数据所有权

| 层级 | 权威来源 | 允许内容 |
|---|---|---|
| 平台级凭据 | `credential-index.yaml` | 账号、密码和凭据元数据；只在内存解析。 |
| 平台级 Runtime | `runtime-value-index.yaml.runtime_values` | URL、host、开关等环境值及显式敏感性分类。 |
| 跨运行状态 | `runtime-value-index.yaml.runtime_state` | 版本序列和分配账本。 |
| 用例级业务数据 | `<case>\branches\<branch>\tests\test-data.json` | 稳定输入和生成规则。 |
| 运行级实际数据 | `runs\<run_id>\reports\resolved-test-data.json` | 本次实际参数、非敏感 Runtime 解析结果和序列分配；凭据只保留引用。 |

## 6. 功能需求

### FR-001 Manifest 驱动验证

验证器必须从目标 release manifest 读取完整附件集合并逐项校验，不维护固定子集。Release 内部损坏、manifest/receipt 身份冲突、路径越界和当前输入漂移必须使用不同错误分类。

### FR-002 全局与项目作用域隔离

全局 Skill 只提供通用引擎；天津路径、case ID、公告字段绑定、定位器和私有引用只能存在于天津项目适配器。天津专属发布/验证脚本不得继续作为全局入口。

### FR-003 分支级 Test Data

每个 A/B 分支必须各自拥有唯一 `tests\test-data.json`，至少包含 `schema_version`、`case_id`、`branch_id`、`parameters`、`generation_rules`、`runtime_refs` 和 `metadata`。文件可人工修改，不保存运行期最终值、凭据值或序列当前值。

### FR-004 完整参数清单

Compiler 必须生成完整 `CASE_PARAMETER_MANIFEST`。固定业务值可显示实际值；普通 Runtime 仅在显式 `sensitive=false` 时展开；未分类或敏感 Runtime、credential、sequence 只保留类型安全引用和元数据。

### FR-005 编译和固定同步

固定同步入口必须支持默认 `dry-run` 和明确 `apply`。计划绑定单一 case+branch、完整输入身份、目标路径、expected active 和计划哈希；apply 前重新读取全部输入，使用 staging、并发门禁、完整附件验证、原子激活和 readback。任何不一致 fail closed。

### FR-006 执行期参数一致性

Playwright 启动时加载一次不可热更新快照，并在启动、每个参数消费点和首次业务写操作前重新计算当前文件哈希。漂移、Guard 故障、日志不可用或快照不可用时，业务写入计数必须为零。

### FR-007 Runtime 影响传播

编译身份必须记录实际引用类型、解析模式和参与 build 的 Runtime 摘要。只有被引用且编译展开的 Runtime 变化才使相关用例 `out_of_sync`；系统时间、时间戳、凭据值和运行期序列分配不改变 build。

### FR-008 产品级诊断状态

产品根必须建立：

```text
diagnostics\unfinished-repairs.json
diagnostics\failure-repair-history\YYYY-MM-DD.jsonl
diagnostics\failure-repair-history\index.json
```

unfinished 按 `issue_fingerprint + case_id + branch_id` 保存当前问题；每日 JSONL 保存全部失败层摘要和修复事件；无事件不创建空日期文件；index 只登记实际存在且已验证的每日文件。

### FR-009 统一日志接口

固定脚本和 Playwright 必须调用同一通用日志接口。接口负责事件 Schema、重复键检查、问题指纹、跨进程排他、逐行 JSON 校验、原始字节哈希、幂等、索引验证、投影恢复和 fail closed。天津适配器不得定义另一格式。

### FR-010 修复完成门禁

参数、测试资产和同步问题的 `repair-completed` 必须提供目标 build、data revision、manifest/hash/readback 证据。非构建类问题必须提供责任层证据和 Codex 审阅引用；不适用字段显式标记。缺少对应证据不得删除 unfinished，历史事件不得删除或改写。

### FR-011 旧格式资产迁移与执行资格

所有旧格式正式资产默认只读、不可执行。开发交付必须同步完成 A/B 当前正式资产、直接共享依赖、产品聚合、active/release 体系和私有索引引用契约的受控迁移。迁移成功并通过验证后才恢复 execution eligibility；历史 release/run/report 保持原样。

### FR-012 清理治理

历史 release、RunResult、报告和 `.codex` 审计记录按保留策略只读保存。`_tmp`、过期备份、缓存和 IDE 文件必须盘点、分类并检查 active 引用、回滚、证据和 hold。实际删除前必须有清单、dry-run、影响报告和独立授权，优先可恢复删除。

### FR-013 运行实际参数快照

每次未来真实执行必须生成不可变 `resolved-test-data.json`。Canonical RunResult 和 evidence index 必须同时记录相对引用与哈希；任一缺失或不一致时，该 run 不得完成或生成有效报告。凭据实际值不得进入快照。

### FR-014 开发完成与真实执行边界

开发与迁移完成以 Schema、编译、manifest/release、哈希、同步、Guard、日志、迁移、清理 dry-run、非回归和模拟零写入验证通过为准。通过后仅表示具备申请真实执行资格；真实 UI/R2 仍需另行授权。

## 7. 业务规则

- BR-001：历史 RunResult 必须按 run_id 独立解释，任何迁移、静态验证、报告或 reconciliation 均不得升级或覆盖原状态。
- BR-002：普通业务值在允许的报告/投影中原样显示；账号密码、Token、Cookie、storage state、Authorization、未授权私有请求载荷和其他安全敏感值禁止出现。私有 URL 不检测、不拦截、不脱敏。
- BR-003：开发优先复用有效本地模块、标准接口和经过许可证/版本/hash 审查的参考代码；无准入证据不得复制或新增依赖。
- BR-004：清理资格不等于删除授权；任何实际删除、移动或覆盖必须单独授权。
- BR-005：Codex 负责架构、Phase/Story、开发和测试方案划分；固定脚本与执行 Agent 不能改变需求、授权或完成状态。

## 8. 非功能需求

- NFR-001 确定性与数据完整性：相同输入产生相同 JCS hash、参数清单、build 和派生物。
- NFR-002 原子性、并发与恢复：并发修改、进程崩溃和部分写入不得产生虚假 active、重复事件或虚假修复完成。
- NFR-003 作用域隔离：通用包不得出现天津路径、case ID、定位器、业务常量或凭据值。
- NFR-004 可追溯与可操作性：从 Goal/FR/AC 可追踪到架构、Story、测试和证据；Codex 可从产品级 diagnostics 定位问题。
- NFR-005 历史兼容与不可变性：旧格式读取器用于审计，旧资产不回写；新执行只允许迁移后的合规资产。
- NFR-006 安全与隐私：凭据值不进入 Source/Test Data、manifest、快照、报告、日志、RAG、Skill 或外部提示。
- NFR-007 依赖与可移植性：优先复用当前锁定依赖和标准库；新依赖需要发现、许可、版本/hash 锁定和安装授权。
- NFR-008 可维护性：接口、状态和错误码稳定；项目适配器可独立演进，不复制通用内核。

## 9. 验收标准

- AC-001：manifest 完整、少项、多项、错误 hash、路径越界和 receipt 冲突 fixture 均产生稳定且正确的错误分类。
- AC-002：全局候选扫描不包含天津路径、A/B case ID、公告定位器或项目适配实现。
- AC-003：A/B 各有唯一合法 test-data，case/branch/hash 强一致，人工修改后所有旧派生物判定 out_of_sync。
- AC-004：Human、Midscene、Resolved、Playwright 和 parameter manifest 的参数事实逐字段一致，凭据和序列只保留引用。
- AC-005：dry-run 零目标写入；apply 缺计划、计划过期、输入变化、并发变化、目标错配和 readback 失败均保留旧 active。
- AC-006：启动、参数消费和首次业务写前任一漂移均终止执行、记录失败并保证业务写入为零。
- AC-007：未引用 Runtime 变化不影响 build；被引用且展开的 Runtime 变化仅影响对应用例。
- AC-008：无事件日期无 JSONL；首条事件创建完整非空文件；每日历史不可覆盖或删除。
- AC-009：JSONL 截断/重复键/Schema 错误、index 缺失/损坏/hash/count 不一致和锁冲突均 fail closed。
- AC-010：无对应证据的 repair-completed 被拒绝；完整修复后才删除 unfinished 投影，历史事件保留。
- AC-011：重新编译后 test_data_hash、data revision、manifest、receipt、全部投影和 active build 一致。
- AC-012：真实 run 的 resolved snapshot、RunResult 和 evidence index 三者引用/hash 完全一致，否则报告无效。
- AC-013：日志、index、unfinished 或修复投影任一步失败时不得错误关闭问题。
- AC-014：历史 release、RunResult、报告和审计记录字节不因迁移或验证而改变；禁止动作均未执行。
- AC-015：A/B 当前正式资产及直接依赖均产生迁移后继并通过验证；不存在仍具执行资格的旧格式正式资产。
- AC-016：清理 inventory 覆盖 `_tmp`、备份、缓存、IDE、staging 和 `.codex`；每项有保留/可清理/hold/待决 disposition，未获授权零删除。
- AC-017：完整离线和模拟零写入测试通过后状态为 execution-ready-not-live-verified，不得宣称真实 UI/R2 通过。
- AC-018：每个复用依赖或参考代码均有来源、许可证、版本/hash、复用分类、改造说明和验证证据；未批准新依赖不进入实现。

## 10. 实施期确认的需求增量

- 服务范围选择必须点击上级“天津市”复选框，并验证和平区及其当前可见后代均处于级联选中状态；不得用逐个子节点点击替代上级选择。
- Playwright 使用与当前 Playwright 版本配套的 Chromium 和 fresh BrowserContext，不再用未受支持的超前系统 Chrome `executable_path` 组合作为正式基线。
- 已认证公告列表路由可作为登录成功证据；菜单入口超时后，只允许同主机、同业务域的创建页受控直达。登录页、跨主机或认证证据不足时禁止 fallback。
- 管理权力归属 Cascader 和服务范围 Tree 在后续字段操作前必须满足确定性关闭后置条件。
- A/B 每个正式 Run 只允许一次可见 UI submit；本轮创建的公告业务数据按 `not_planned_this_release` 保留，不纳入文件清理。
- 所有历史失败 Run 保持原始状态；新的成功 Run 不能升级或覆盖旧 RunResult。

## 11. 最终交付与验收边界

- 全局通用引擎、天津项目适配器、正式 A/B 后继 release、产品 aggregate、执行期 Guard、日志与精确清理均属于本次交付。
- 全局包只含通用契约与引擎；天津路径、业务定位器、用例数据和私有运行值只留在项目侧，不进入公开 Skill。
- 正式验收要求 A/B 各有一个独立 canonical 成功 RunResult，且 `submit_count=1`、`write_state=write_succeeded_verified`。
- 文件清理只处理计划绑定的 cache/IDE 对象；禁止删除测试创建的公告、历史 release、run、报告或治理审计记录。
- GitHub 发布只包含可公开的全局 `ui-test` 与脱敏治理文档；正式项目资产、私有 URL、凭据和运行证据原文不发布。

## 12. 当前验收摘要

截至本回顾调整：全局 Skill 安装时证据为 241 项测试通过，本轮 GitHub 发布前对当前安装树重跑为 234 项通过；项目适配器为 25 项测试通过；A/B 正式 Run 均通过；正式 A/B 与产品 active 为 `valid/in_sync/ready`；336 个历史文件未变化；精确清理删除 21 个 cache/IDE 目录且未删除业务或历史资产；产品未完成修复投影为空。

## 13. 追踪与版本治理

逐项 Requirement → AC → Architecture → Story → Task → TCOV → EVD 映射见 RTM v1.2。v0.5 取代 v0.4 作为完整需求基线；v0.3 及更早版本只用于审计和来源追溯。
