# UI-Test 参数治理、迁移与失败修复开发计划

状态：`completed-as-built / 已按落地实现完成`  
规范 Envelope：`envelopes/development-plan-v0.4.envelope.json`  
需求锚点：`RA-UI-TEST-REPAIR-20260830@v0.7`  
说明：旧版本保持只读；本文件是当前后继版本，不回写历史文档。

## 1. 执行边界

本计划是未来实施的精确输入，不授权立即执行。

固定候选根：

```text
<workspace>\work\ui-test-repair-candidate-20260902
```

候选布局：

```text
ui-test-repair-candidate-20260902\
  ui-test\                       # 通用 Skill 候选
  project-adapter\
    tianjin-ops-platform-announcement-create\
  migration-fixture\             # D 盘正式树的受控副本
  evidence\
  manifests\
```

禁止把 `work\workspace-copy-20260831` 作为实现输入。全局 Skill 和 `<formal-root>` 在候选阶段均只读。

## 2. 复用与依赖策略

1. 先复用现有 `jsonschema`、`rfc8785`、JCS、Runtime/Credential Loader、Path Planner、Compiler 骨架、Registry Validator、Migration、RunResult/Evidence 和现有测试；
2. `jsonpointer`、`portalocker` 为条件复用候选，必须先检查机器级 PATH、`C:\DevelopTool` 和已安装包；
3. 已存在且版本/许可证/hash 合格时，可在候选内使用并更新依赖记录；
4. 不存在时不得自动安装，必须提交独立依赖准入；未获批准时使用经过测试的 RFC 6901/标准库 fallback；
5. 禁止复制天津专属发布/验证脚本作为通用引擎；它们只作为反例和迁移输入。

## 3. 任务依赖图

```text
TASK-001 clean candidate
  -> TASK-002 dependency admission
  -> TASK-003 contracts
  -> TASK-004 test-data/runtime resolver
  -> TASK-005 compiler/renderers
  -> TASK-006 verifier/state
  -> TASK-007 plan-bound sync
  -> TASK-008 guard/snapshot
  -> TASK-009 diagnostics/recovery
  -> TASK-010 run/evidence/report linkage
  -> TASK-011 Tianjin adapter and A/B migration candidate
  -> TASK-012 migration package and execution eligibility
  -> TASK-013 cleanup inventory and dry-run
  -> TASK-014 full QA
  -> TASK-015 landed review and completion decision
```

## 4. 任务定义

### TASK-001：建立干净候选基线

- Story：UIR-ST-001。
- 输入：全局有效 `ui-test`、源 manifest/hash、排除清单。
- 文件：候选根全部目录、`manifests\source-baseline.json`、`manifests\candidate-initial.json`。
- 动作：复制有效包；排除 `.pytest_cache`、`__pycache__`、`.pyc`、`.idea`、项目失败日志和天津专属项目资产；记录每个文件 hash。
- 验证：源/候选差异仅为允许排除项；误写 workspace 零引用；候选结构 validator 通过。
- 回滚：删除本次新候选根；全局和 D 盘零修改。

### TASK-002：依赖和参考代码准入

- Story：UIR-ST-001、UIR-ST-015。
- 输入：参考评审、现有 lock、机器依赖发现。
- 文件：候选 `requirements.lock`、`dependency-licenses.json`、拟新增 `THIRD-PARTY-NOTICES`/SBOM。
- 动作：确认 jsonschema/rfc8785 复用；评估 jsonpointer/portalocker；固定版本、wheel/source hash、许可证、上游测试 commit；无安装授权时选择 fallback。
- 验证：未批准依赖零引入；许可证和来源完整；依赖变化有独立 approval reference。
- 回滚：恢复原 lock/license manifest；不卸载机器已有包。

### TASK-003：完整契约族和 Registry

- Story：UIR-ST-002、UIR-ST-003。
- 目标文件：
  - `schemas/test-data.schema.json`
  - `schemas/case-parameter-manifest.schema.json`
  - Source/Case IR/Resolved/Manifest/Receipt v2
  - compile/sync plan/result、sync-state、resolved-test-data
  - failure/repair event、history index、unfinished
  - migration inventory/plan/result、cleanup inventory/plan/result
  - `schemas/contract-registry.json`
- 接口：Draft 2020-12；v1 保留 audit-readable，新写 v2。
- 验证：每个 Schema 正反 fixture、`check_schema`、registry/source baseline validator；额外字段、重复键和身份错配失败。
- 回滚：删除新增 v2 契约并恢复 registry；v1 文件未改写。

### TASK-004：Strict Loader、Test Data 和 Typed Resolver

- Story：UIR-ST-004。
- 目标文件：`scripts/ui_test_core/test_data_contracts.py`、Runtime Loader/Schema 的分类扩展、对应测试。
- 消费：StrictLoad、Runtime/Credential Loader、RFC 6901、JCS。
- 产生：validated test-data、data revision、typed refs、runtime material digest、CASE_PARAMETER_MANIFEST。
- 行为：拒绝重复键、NaN/Infinity、非法引用和 scope 错配；只有显式非敏感普通 Runtime 展开；credential/sequence 引用-only。
- 验证：RFC 6901 官方向量、键序/空白不漂移、语义变化必漂移、引用碰撞和敏感边界。
- 回滚：兼容层不接入 Compiler；现有 Runtime/Credential Loader 行为保持。

### TASK-005：Compiler v2 和一致 Renderer

- Story：UIR-ST-005。
- 目标文件：`case_contracts.py`、`compiler.py`、v2 renderer、产品聚合器和测试。
- 消费：Source Case v2、Test Data、typed refs、dependency graph、config fingerprint。
- 产生：Case IR、Resolved IR、Human、Midscene、Playwright、parameter manifest、receipt、manifest。
- 行为：删除重复 renderer；复合 case+branch key；manifest 列出所有非自身附件；所有投影共享一份参数清单。
- 验证：逐字段一致、生成 Python `compile()`、输入对象不变、敏感/credential/sequence 值不出现在产物、v1 只读回归。
- 回滚：v2 编译入口关闭；v1 只读验证不变。

### TASK-006：Manifest Verifier 和三轴状态

- Story：UIR-ST-006。
- 目标文件：新增 `release_verifier.py`、sync-state evaluator、Schema 和测试。
- 消费：active、manifest、receipt、实际文件集合、current input identity。
- 产生：release_integrity、input_sync、execution_gate、稳定 issue list。
- 行为：路径 containment、完整集合、hash、identity、current drift 分开判断；不可变 manifest 不写回 out_of_sync。
- 验证：少项、多项、路径逃逸、错误 hash、receipt/active 冲突、source/test-data/runtime drift。
- 回滚：不激活新 verifier；现有 verifier 保持只读。

### TASK-007：固定 Compile/Sync Coordinator

- Story：UIR-ST-007。
- 目标文件：新增 `case_sync.py` 与 CLI wrapper；扩展 Path Planner；对应测试。
- 接口：`dry_run(inputs,target)`、`apply(plan_hash,input_loader,target)`、`validate_release_integrity`。
- 行为：默认 dry-run；apply 重读输入、单 case+branch、跨进程排他锁、双 CAS、唯一 staging、manifest 验证、原子 pointer 和 readback。
- 验证：目录树零写 dry-run、计划篡改/过期、双进程、staging 故障、existing release、replace/readback 失败、重复 apply no-op。
- 回滚：清理本次 operation staging；旧 active 和历史 release 保持。

### TASK-008：Execution Data Session 与 Resolved Snapshot

- Story：UIR-ST-008。
- 目标文件：Guard、Snapshot Writer、Automation Runtime 接口、RunResult Schema 前置扩展和测试。
- 行为：Guard 在 BrowserContext 前启动；所有参数经受控 session 消费；snapshot 成功封存且首写前再次校验后才允许业务写。
- 验证：三时点漂移、日志/快照故障、不可变 snapshot、凭据引用-only、零 BrowserContext/零业务请求/零提交。
- 回滚：参数化 v2 用例禁止执行；legacy 审计不受影响。

### TASK-009：Failure/Repair Event Store

- Story：UIR-ST-009。
- 目标文件：统一 Recorder、锁抽象、恢复逻辑、Schema 和多进程测试。
- 行为：China log date、JSONL 权威源、index/unfinished 投影、持久化事务意图、同幂等键恢复、受控 rebuild、typed repair gate。
- 验证：无事件无文件、首条非空原子创建、截断/重复键/index mismatch、跨日幂等、多进程、各故障点恢复、无证据 repair 拒绝。
- 回滚：候选 diagnostics fixture 删除；正式产品 diagnostics 不创建。

### TASK-010：RunResult、Evidence 和报告链接

- Story：UIR-ST-010。
- 目标文件：RunResult/evidence/report Schema、`run_governance.py`、报告 validator 和测试。
- 行为：三者保存 snapshot 相对引用/hash；任一不一致阻断 completion/report；历史 RunResult 只读。
- 验证：分别篡改 ref/hash/snapshot、缺失文件、历史字节 hash 前后对比。
- 回滚：新 run 链接功能关闭；历史结果不变。

### TASK-011：天津适配器和 A/B 迁移候选

- Story：UIR-ST-011。
- 目标文件：`project-adapter\tianjin-ops-platform-announcement-create` 下 A/B test-data、路径/字段 adapter、Flow/Page/Component 绑定、迁移映射和测试。
- 输入：只读正式 A/B Source/IR/runner、8 个共享非缓存依赖和私有索引引用。
- 行为：迁移标题、内容、来源、类型、归属、范围、受众、失效规则和 sequence ref；不复制凭据值；天津逻辑不进入通用包。
- 验证：A/B 唯一 test-data、完整参数、业务规则和依赖闭包；通用包天津标识零发现。
- 回滚：删除项目候选；D 盘零修改。

### TASK-012：迁移包和 Execution Eligibility 演练

- Story：UIR-ST-012。
- 目标：`migration-fixture`、迁移 inventory/plan/result、后继 release、active 候选、产品聚合和证据。
- 行为：在 D 产品树副本上运行计划绑定迁移；历史 release/run/report 不改写；新后继只标记 execution-ready-not-live-verified。
- 验证：迁移前后历史 hash 相同、current old-format execution eligibility 为零、新后继全门禁通过、正式 apply 命令仅预览。
- 回滚：删除 migration fixture；正式 D 盘零修改。

### TASK-013：清理 Inventory 和零删除 Dry-run

- Story：UIR-ST-013。
- 目标文件：cleanup inventory/plan/result、引用图和 retention/hold 报告。
- 范围：历史 release/run/report/.codex、`_tmp` 24 组、备份、缓存、IDE、空 staging。
- 行为：每项分类为 retain、cleanup-eligible、hold、unresolved；不执行删除。
- 验证：D 根 inventory 全覆盖；dry-run 前后 inventory hash `f66f...ee36` 不变；无 broad target/glob；每个 cleanup-eligible 有引用和恢复证据。
- 回滚：无状态变更，仅删除候选报告。

### TASK-014：全量 QA

- Story：UIR-ST-014、UIR-ST-015。
- 动作：运行 focused → integration → full suite → sensitive/scope scan → migration/cleanup rehearsal → rollback drill。
- 命令基线：使用已发现的 `<python-runtime> -B -m pytest`，禁用缓存；不得安装缺失项。
- 证据：EVD-001～EVD-018，包含输入 hash、命令、stdout/stderr/exit、失败归因、文件清单和回滚状态。
- 出口：P0/P1 零开放；任何缺失关键验证保持 repair-needed。

### TASK-015：Landed Review 与完成判定

- Story：UIR-ST-016。
- 输入：Anchor v0.4、变更 manifest、RTM、全部证据和独立 QA 结论。
- 动作：landed review、document manifest、CompletionEvaluator；检查 unmapped action、semantic drift、许可和敏感边界。
- 输出：candidate-development-complete 或 repair-needed。未正式迁移时整体状态继续 waiting-approval；不得宣称 live verified。
- 回滚：不发布、不安装；候选保持可审阅。

## 5. 授权门禁

| Gate | 独立授权后才允许 |
|---|---|
| GATE-IMPL | 创建候选代码、运行本地测试 |
| GATE-DEP | 新增/安装 jsonpointer、portalocker 或其他依赖 |
| GATE-GLOBAL | 安装/修改全局 ui-test Skill |
| GATE-FORMAL | 写入正式 D 盘、发布后继 release、切换 active |
| GATE-CLEANUP | 实际删除、移动或覆盖清理对象 |
| GATE-R2 | 真实 UI/R2/R3 |
| GATE-RAG-PUBLISH | D:/RAG 或外部发布 |

一个 Gate 的授权不能传递给其他 Gate。

## 6. 开发出口

候选开发完成必须满足：

- 所有 Story 和 AC 具有通过证据；
- 复用和依赖许可证可追踪；
- A/B migration fixture 完整且历史 hash 不变；
- cleanup 仅 dry-run，实际删除为零；
- 业务写模拟计数为零；
- 未修改全局 Skill、正式 D 盘、RAG 和历史结果；
- 最终状态明确区分 candidate complete、formal migration waiting approval 和 live not verified。


## 7. As-Built Task 状态

| Task | 最终状态 | 主要结果 |
|---|---|---|
| TASK-001 | passed | 候选基线、依赖与许可证边界完成 |
| TASK-002 | passed | v2 契约族和严格加载完成 |
| TASK-003 | passed | 历史只读、新写 v2 边界完成 |
| TASK-004 | passed | Test Data、typed refs、Runtime 摘要完成 |
| TASK-005 | passed | Compiler v2、全部投影和参数清单完成 |
| TASK-006 | passed | manifest-driven verifier 和三轴状态完成 |
| TASK-007 | passed | plan-bound dry-run/apply、CAS 与 readback 完成 |
| TASK-008 | passed | Guard、resolved snapshot 和业务首写门禁完成 |
| TASK-009 | passed | 每日 JSONL、index、unfinished 与 repair gate 完成 |
| TASK-010 | passed | RunResult/evidence/snapshot 链接完成 |
| TASK-011 | passed | 天津 A/B 适配器与全局作用域隔离完成 |
| TASK-012 | passed | A/B 后继 release、产品 aggregate 与 active 切换完成 |
| TASK-013 | passed | 计划绑定 cache/IDE 精确清理完成，保护对象零删除 |
| TASK-014 | passed | 全局安装时 241 项、本轮发布前当前树 234 项、项目 25 项、正式验证和 R2 通过 |
| TASK-015 | passed | Landed Review、逐项 RTM、运行时文档 manifest 和 CompletionEvaluator 完成 |

## 8. 回滚与保留

- 正式发布的回滚基线由 r21 部署备份记录绑定；不会通过改写历史 release 实现回滚。
- cache/IDE 清理对象可由工具重建，不恢复旧缓存。
- 公告业务数据不属于文件清理对象；A/B 成功 Run 和所有历史失败 Run 均保留。
