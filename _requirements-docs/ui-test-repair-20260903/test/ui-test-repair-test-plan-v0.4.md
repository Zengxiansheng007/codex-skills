# UI-Test 参数治理、迁移与失败修复测试方案

状态：`passed-as-tested / 已验证`  
规范 Envelope：`envelopes/test-plan-v0.4.envelope.json`  
需求锚点：`RA-UI-TEST-REPAIR-20260830@v0.7`  
说明：旧版本保持只读；本文件是当前后继版本，不回写历史文档。

## 1. 测试目标与边界

本方案证明候选实现满足参数唯一来源、确定性编译同步、执行期零写门禁、失败修复记录、A/B 迁移、清理 dry-run、历史不可变和供应链治理。

本方案不执行：

- 真实 UI 或 R2/R3；
- 全局 Skill 安装；
- 正式 D 盘写入/active 切换；
- 实际删除；
- 依赖安装；
- RAG 或外部发布。

最终测试结论只能是 `execution-ready-not-live-verified`，不能声称业务系统已真实验证。

## 2. 风险分级

| 风险 | 等级 | 主要覆盖 |
|---|---:|---|
| 旧参数或旧 release 绕过新门禁继续执行 | P0 | TCOV-003/005/006/015/017 |
| Source Case 与 Test Data 再次形成双重来源 | P0 | TCOV-003/004 |
| Guard、日志或快照失败后仍触发业务写 | P0 | TCOV-006/012/017 |
| manifest 附件少校验、误报或漏报 | P1 | TCOV-001/002 |
| dry-run 后输入/active 并发变化导致覆盖 | P1 | TCOV-005/013 |
| JSONL/index/unfinished 部分写入或虚假修复完成 | P1 | TCOV-008/009/010/013 |
| 凭据、敏感 Runtime 或序列值进入产物 | P1 | TCOV-004/012 |
| 迁移改写历史 release/run/report | P1 | TCOV-014/015 |
| 清理误删证据、回滚基线或全局 Skill 备份 | P1 | TCOV-016 |
| 第三方代码许可证/版本/hash 不可追溯 | P1 | TCOV-018 |
| 全局候选混入天津路径和定位器 | P1 | TCOV-011 |

## 3. 测试层级

1. Schema/Contract：Draft 2020-12 正反 fixture、Schema 自校验、registry；
2. Unit：Strict Loader、JCS、Pointer、typed refs、state evaluator、event fingerprint；
3. Component：Compiler/renderers、Verifier、Sync、Guard、Event Store、Migration/Cleanup Planner；
4. Integration：端到端候选编译同步、运行快照、日志恢复、A/B migration fixture；
5. Concurrency/Recovery：多进程锁、CAS、故障注入、幂等恢复；
6. Regression：全局有效基线 legacy 测试和新 v2 测试；
7. Static/Security：作用域、敏感、许可证、依赖、路径 containment；
8. Landed Review：changed files、RTM、证据和完成状态。

## 4. 覆盖项

### TA-001 Contract 与 Strict JSON

- TCOV-001：manifest/receipt/active/附件完整集合和错误分类；
- TCOV-003：Test Data、参数清单和 case/branch 身份；
- TCOV-008：failure/repair event、daily index、unfinished；
- TCOV-012：resolved snapshot、RunResult/evidence 链接；
- TCOV-015：migration inventory/plan/result；
- TCOV-016：cleanup inventory/plan/result。

验证：合法/缺字段/额外字段/错误类型/未知版本/重复键/非法 UTF-8/NaN/Infinity/Schema 自身非法。

### TA-002 Canonical Hash、Pointer 与 Runtime

- TCOV-004：RFC 8785、RFC 6901、typed refs 和 Runtime digest；
- TCOV-007：精准 Runtime 影响传播。

验证：键序和空白不改变 JCS；语义变化改变 hash；Pointer 解码顺序、数组前导零、`-`、缺失路径均按 RFC 6901；credential/sequence 永不展开；未分类 Runtime 引用-only。

### TA-003 Compiler 与 Projection

- TCOV-001：manifest-driven 附件；
- TCOV-004：完整参数清单；
- TCOV-011：重新编译一致性。

验证：Human/Midscene/Resolved/Playwright/parameter manifest 逐字段一致；生成 Python 可编译；输入对象不被修改；同 case 不同 branch 不覆盖；Compiler 顶层函数无重复定义。

### TA-004 Verifier 和状态模型

- TCOV-002：release integrity 与 input sync 分离；
- TCOV-007：referenced Runtime 精准影响；
- TCOV-017：execution gate。

验证：缺 manifest、少/多附件、hash 错误、路径越界、receipt/active 冲突、source/test-data/dependency/runtime/config 漂移分别产生稳定状态和 error code。

### TA-005 Plan-bound Sync

- TCOV-005：dry-run/apply、计划绑定、幂等；
- TCOV-013：并发与失败恢复。

验证：dry-run 前后目录树完全一致；apply 无计划、计划篡改、计划过期、目标错配均失败；双进程只允许一个激活；staging、replace、readback 故障保留旧 active；existing identical release 可幂等激活，冲突 release 拒绝。

### TA-006 Guard、Snapshot 和零业务写

- TCOV-006：启动、消费、首次业务写前门禁；
- TCOV-012：snapshot 三向链接；
- TCOV-017：无真实 UI 的完成边界。

验证：三个检查点分别修改参数；Guard/Recorder/Snapshot 故障；BrowserContext factory、提交方法和业务写请求 spy 均为零。稳定路径使用 function-scoped non-persistent context。网络模拟设置 Service Worker block 并拦截所有业务写请求。

### TA-007 Event Store、投影和 Repair Gate

- TCOV-008：每日文件生命周期；
- TCOV-009：Schema、锁、原始字节 hash、index；
- TCOV-010：repair-completed 类型化证据；
- TCOV-013：事务恢复。

验证：无事件无文件、首条非空创建、中国日期边界、跨日幂等、多进程唯一事件；在 intent、append、fsync、index、unfinished、readback 各点注入失败；相同幂等键恢复、不同请求阻断；无证据修复不删除 unfinished。

### TA-008 RunResult、Evidence 和报告

- TCOV-012：snapshot/RunResult/evidence/ref/hash；
- TCOV-014：历史资产不变。

验证：分别篡改 snapshot、ref、hash 和 evidence；completion/report 必须失败；历史 RunResult 和报告 hash 前后相同；私有 URL 不作为扫描项，其他禁止敏感值零发现。

### TA-009 A/B Migration

- TCOV-003：A/B 唯一 Test Data；
- TCOV-011：新投影和产品聚合；
- TCOV-014/015：历史不改写和后继执行资格。

验证：迁移 inventory 覆盖2个 Source Case、23个 case release、3个 run、19个产品 release 和直接共享依赖；历史 hash 不变；current old-format eligibility 为零；新后继在复制 fixture 中通过全部门禁；状态仅 execution-ready-not-live-verified。

### TA-010 Cleanup Governance

- TCOV-016：retain/cleanup-eligible/hold/unresolved disposition。

验证：覆盖 `_tmp` 24 组/1783文件、历史资产、全局 Skill 备份、`.codex`、缓存、IDE 和13个空 staging；每个可清理项有引用/回滚/hold 检查；dry-run 前冻结当前 inventory hash（2026-09-02 参考值为 `sha256:f66f32e1b55f4e3c2133ae365bb22c14cd2dce9ec34c1be3550e5c0e2ff2ee36`），dry-run 后与本次冻结值一致；实际删除为零。

### TA-011 Scope、Sensitive 与供应链

- TCOV-002/011：通用包天津标识零发现；
- TCOV-012：禁止敏感值零发现；
- TCOV-018：依赖许可证、版本/hash 和 NOTICE/SBOM。

验证：扫描全局候选、项目适配器边界、所有产物、报告和日志；未批准依赖未进入 lock/import；直接复用代码保留许可和来源。

### TA-012 Full Regression 与 Landed Review

- TCOV-017：完整离线候选完成；
- TCOV-018：复用治理；
- 覆盖全部 TCOV/EVD。

验证：focused 和 full suite、敏感/作用域扫描、migration/cleanup rehearsal、rollback drill、landed review、document manifest 和 CompletionEvaluator。

## 5. 测试数据

- 合成 A/B Source/Test Data/Runtime/Credential key fixture；凭据值使用占位并不得写入证据；
- 合成依赖图、active/release、manifest、receipt 和多分支冲突；
- 临时目录模拟 JSONL/index/unfinished 和各故障点；
- 只读复制正式 D 盘产品树作为 migration fixture；不读取或复制私有值；
- 清理测试只使用路径/大小/inventory hash 和 synthetic disposition；
- 真实 URL、真实 UI 和真实 R2 不进入自动化测试输入。

## 6. 环境与依赖

- 先检查机器级 PATH 和 `C:\DevelopTool`；计划使用现有 `<python-runtime>`；
- 使用当前锁定 jsonschema、rfc8785、pytest、PyYAML；
- jsonpointer/portalocker 只有依赖准入和安装授权后才可使用；
- 不自动创建 venv、不安装包、不安装 Playwright 浏览器、不启用 xdist；
- pytest 使用 `-B`、禁用 cache provider，并将所有写入限制在授权候选或系统临时目录。

## 7. 入口门禁

- Requirements v0.3、Anchor v0.4、Architecture v0.2、Development v0.2、Phase/Story 和 RTM 已批准；
- 获得精确候选根实施/测试授权；
- 有效全局基线和 D inventory 重新 hash；
- 误写 workspace 明确排除；
- 依赖现状和 license manifest 可读；
- 禁止动作和零写 spy 已配置。

## 8. 出口门禁

- AC-001～018 均有通过证据；
- P0/P1 失败为零，P2 已说明或修复；
- focused/full tests 通过且无未归因失败；
- historical hashes 不变；
- D 盘和全局 Skill 写入为零；
- actual cleanup 删除为零；
- real UI/R2 调用为零；
- 敏感和天津作用域扫描通过；
- 依赖和参考代码来源/许可/hash 完整；
- 最终状态为 candidate-development-complete / formal-migration-waiting-approval / live-not-verified。

## 9. 证据契约

| EVD | 证据 |
|---|---|
| EVD-001 | Manifest Verifier 正反结果与完整附件清单 |
| EVD-002 | 全局/天津作用域扫描 |
| EVD-003 | Test Data Schema、身份和唯一来源测试 |
| EVD-004 | 参数清单与 renderer 一致性 |
| EVD-005 | Sync dry-run/apply、计划和并发测试 |
| EVD-006 | Guard 三检查点与零业务写 spy |
| EVD-007 | Runtime 影响图和 digest 精准性 |
| EVD-008 | 每日 JSONL 生命周期 |
| EVD-009 | JSONL/index/hash/锁损坏测试 |
| EVD-010 | Repair Gate 类型化证据测试 |
| EVD-011 | 编译、receipt、manifest、active 一致性 |
| EVD-012 | Resolved Snapshot/RunResult/Evidence 链接 |
| EVD-013 | 事务、崩溃和幂等恢复 |
| EVD-014 | 历史 release/run/report 不变证明 |
| EVD-015 | A/B migration fixture 和 eligibility 结果 |
| EVD-016 | Cleanup inventory/disposition/零删除 dry-run |
| EVD-017 | Full suite、模拟零写入和 completion 状态 |
| EVD-018 | 依赖许可证、版本/hash、NOTICE/SBOM 和上游测试来源 |

每份证据必须记录：输入 hash、命令/方法、运行环境、时间、exit/status、stdout/stderr 摘要、失败归因、产物路径和回滚状态。计划中的 EVD 在执行前状态均为 `planned`，不得当成已有通过证据。

## 10. 计划验证命令

实施授权后，按实际候选路径执行：

```powershell
& '<python-runtime>' -B -m pytest -p no:cacheprovider -q '<workspace>\work\ui-test-repair-candidate-20260902\ui-test\tests\test_test_data_contracts.py'
& '<python-runtime>' -B -m pytest -p no:cacheprovider -q '<workspace>\work\ui-test-repair-candidate-20260902\ui-test\tests\test_compiler_v2.py' '<workspace>\work\ui-test-repair-candidate-20260902\ui-test\tests\test_case_sync.py'
& '<python-runtime>' -B -m pytest -p no:cacheprovider -q '<workspace>\work\ui-test-repair-candidate-20260902\ui-test\tests\test_execution_parameter_guard.py' '<workspace>\work\ui-test-repair-candidate-20260902\ui-test\tests\test_failure_repair_store.py'
& '<python-runtime>' -B -m pytest -p no:cacheprovider -q '<workspace>\work\ui-test-repair-candidate-20260902\ui-test\tests'
```

上述绝对候选根必须在实际 implementation authorization 中逐字匹配；本方案不执行这些命令。

## 11. As-Tested 结果

| TCOV | 结果 | 证据摘要 |
|---|---|---|
| TCOV-001 | passed | manifest 附件集合与错误分类回归 |
| TCOV-002 | passed | 全局/项目作用域扫描，天津专属实现未进入全局包 |
| TCOV-003 | passed | A/B 各自唯一 Test Data 与身份校验 |
| TCOV-004 | passed | 参数清单和各 renderer 一致 |
| TCOV-005 | passed | plan-bound 同步、幂等、CAS 与 readback |
| TCOV-006 | passed | 启动、消费点和首次业务写前 Guard |
| TCOV-007 | passed | 被引用 Runtime 精确影响传播 |
| TCOV-008 | passed | 每日 JSONL 生命周期与无事件不建文件 |
| TCOV-009 | passed | JSONL/index/hash/锁损坏 fail closed |
| TCOV-010 | passed | repair-completed 证据门禁 |
| TCOV-011 | passed | A/B release 与产品 aggregate 为 valid/in_sync/ready |
| TCOV-012 | passed | A 成功 Run 的 snapshot/RunResult/evidence 链 |
| TCOV-013 | passed | B 成功 Run 与 popup sequence 分配 |
| TCOV-014 | passed | 上级天津市级联选中与可见后代断言 |
| TCOV-015 | passed | 336 个历史文件未改变 |
| TCOV-016 | passed | 21 个 cache/IDE 目录精确清理，保护对象零删除 |
| TCOV-017 | passed | A/B 单次 submit、业务写后验证和公告保留 |
| TCOV-018 | passed | 禁止凭据输出、依赖清单和作用域治理 |

测试结论只依据哈希绑定的本地证据摘要；公开文档不复制私有 URL、凭据、页面载荷或正式运行证据原文。
