# UI-Test 修复统一需求追踪矩阵

状态：`passed / 已逐项复核`  
规范 Envelope：`envelopes/rtm-v1.2.envelope.json`  
需求锚点：`RA-UI-TEST-REPAIR-20260830@v0.7`  
说明：旧版本保持只读；本文件是当前后继版本，不回写历史文档。

状态说明：每一行均以当前落地实现和实际证据复核；旧版计划状态保留在被取代的 v1.0/v1.1 文档中。

| Goal | Requirement | Acceptance | Architecture / ADR | Story | Task | TCOV | Evidence | Status |
|---|---|---|---|---|---|---|---|---|
| GOAL-002 | FR-001 Manifest 驱动验证 | AC-001 | ARC-004；ADR-004、ADR-005 | UIR-ST-005、UIR-ST-006 | TASK-005、TASK-006 | TCOV-001、TCOV-002 | EVD-001 | passed / 已通过 |
| GOAL-005 | FR-002 全局/项目隔离 | AC-002 | ARC-001、ARC-009 | UIR-ST-001、UIR-ST-011 | TASK-001、TASK-011 | TCOV-002、TCOV-011 | EVD-002 | passed / 已通过 |
| GOAL-001 | FR-003 分支 Test Data | AC-003 | ARC-001、ARC-002、ARC-009；ADR-001、ADR-003 | UIR-ST-002、UIR-ST-004、UIR-ST-011 | TASK-003、TASK-004、TASK-011 | TCOV-003 | EVD-003 | passed / 已通过 |
| GOAL-001、GOAL-002 | FR-004 完整参数清单 | AC-004、AC-011 | ARC-002、ARC-003；ADR-001、ADR-003 | UIR-ST-004、UIR-ST-005 | TASK-004、TASK-005 | TCOV-004、TCOV-011 | EVD-004、EVD-011 | passed / 已通过 |
| GOAL-002 | FR-005 编译与同步 | AC-005、AC-011、AC-013 | ARC-003、ARC-005；ADR-006 | UIR-ST-005、UIR-ST-007 | TASK-005、TASK-007 | TCOV-005、TCOV-011、TCOV-013 | EVD-005、EVD-011、EVD-013 | passed / 已通过 |
| GOAL-002、GOAL-005 | FR-006 执行期一致性 | AC-006、AC-017 | ARC-006；ADR-008 | UIR-ST-008 | TASK-008 | TCOV-006、TCOV-017 | EVD-006、EVD-017 | passed / 已通过 |
| GOAL-002 | FR-007 Runtime 影响传播 | AC-007 | ARC-002、ARC-004；ADR-003、ADR-005 | UIR-ST-004、UIR-ST-006 | TASK-004、TASK-006 | TCOV-007 | EVD-007 | passed / 已通过 |
| GOAL-003 | FR-008 产品级诊断状态 | AC-008、AC-013 | ARC-007；ADR-007 | UIR-ST-002、UIR-ST-009 | TASK-003、TASK-009 | TCOV-008、TCOV-013 | EVD-008、EVD-013 | passed / 已通过 |
| GOAL-003 | FR-009 统一日志接口 | AC-009、AC-013 | ARC-007；ADR-007 | UIR-ST-002、UIR-ST-009 | TASK-003、TASK-009 | TCOV-009、TCOV-013 | EVD-009、EVD-013 | passed / 已通过 |
| GOAL-003 | FR-010 修复完成门禁 | AC-010、AC-013 | ARC-007；ADR-007 | UIR-ST-009 | TASK-009 | TCOV-010、TCOV-013 | EVD-010、EVD-013 | passed / 已通过 |
| GOAL-004 | FR-011 旧资产迁移与资格 | AC-014、AC-015 | ARC-008、ARC-009；ADR-002 | UIR-ST-003、UIR-ST-011、UIR-ST-012 | TASK-003、TASK-011、TASK-012 | TCOV-014、TCOV-015 | EVD-014、EVD-015 | passed / 已通过 |
| GOAL-004、GOAL-005 | FR-012 清理治理 | AC-014、AC-016 | ARC-008；ADR-010 | UIR-ST-013 | TASK-013 | TCOV-014、TCOV-016 | EVD-014、EVD-016 | passed / 已通过 |
| GOAL-003 | FR-013 运行参数快照 | AC-012 | ARC-006、ARC-010；ADR-008 | UIR-ST-008、UIR-ST-010 | TASK-008、TASK-010 | TCOV-012 | EVD-012 | passed / 已通过 |
| GOAL-005 | FR-014 开发/真实执行边界 | AC-017 | ARC-006、ARC-008、ARC-010 | UIR-ST-012、UIR-ST-014、UIR-ST-016 | TASK-012、TASK-014、TASK-015 | TCOV-017 | EVD-017 | passed / 已通过 |
| GOAL-003、GOAL-005 | BR-001 历史 RunResult 保真 | AC-014 | ARC-010；ADR-002 | UIR-ST-003、UIR-ST-010 | TASK-003、TASK-010 | TCOV-014 | EVD-014 | passed / 已通过 |
| GOAL-001、GOAL-005 | BR-002 输出与敏感政策 | AC-004、AC-012、AC-014 | ARC-001、ARC-002、ARC-006、ARC-007、ARC-010 | UIR-ST-002、UIR-ST-004、UIR-ST-008、UIR-ST-009、UIR-ST-010 | TASK-003、TASK-004、TASK-008、TASK-009、TASK-010 | TCOV-004、TCOV-012 | EVD-004、EVD-012 | passed / 已通过 |
| GOAL-005 | BR-003 参考代码复用 | AC-018 | ADR-009 | UIR-ST-001、UIR-ST-015 | TASK-001、TASK-002、TASK-014 | TCOV-018 | EVD-018 | passed / 已通过 |
| GOAL-004、GOAL-005 | BR-004 删除单独授权 | AC-016 | ARC-008；ADR-010 | UIR-ST-013 | TASK-013 | TCOV-016 | EVD-016 | passed / 已通过 |
| GOAL-005 | BR-005 Codex 控制面 | AC-017、AC-018 | Codex control plane；ADR-009 | UIR-ST-016 | TASK-015 | TCOV-017、TCOV-018 | EVD-017、EVD-018 | passed / 已通过 |
| GOAL-001、GOAL-002 | NFR-001 确定性与完整性 | AC-001、AC-003、AC-004、AC-011 | ARC-001、ARC-002、ARC-003、ARC-004；ADR-004、ADR-006 | UIR-ST-002、UIR-ST-004、UIR-ST-005、UIR-ST-006 | TASK-003、TASK-004、TASK-005、TASK-006 | TCOV-001、TCOV-003、TCOV-004、TCOV-011 | EVD-001、EVD-003、EVD-004、EVD-011 | passed / 已通过 |
| GOAL-002、GOAL-003 | NFR-002 原子、并发与恢复 | AC-005、AC-008、AC-009、AC-013 | ARC-005、ARC-007；ADR-006、ADR-007 | UIR-ST-007、UIR-ST-009 | TASK-007、TASK-009 | TCOV-005、TCOV-008、TCOV-009、TCOV-013 | EVD-005、EVD-008、EVD-009、EVD-013 | passed / 已通过 |
| GOAL-005 | NFR-003 作用域隔离 | AC-002 | ARC-009 | UIR-ST-001、UIR-ST-011 | TASK-001、TASK-011 | TCOV-002、TCOV-011 | EVD-002 | passed / 已通过 |
| GOAL-003、GOAL-004 | NFR-004 追溯与可操作性 | AC-008、AC-010、AC-012、AC-015、AC-016 | ARC-007、ARC-008、ARC-010 | UIR-ST-009、UIR-ST-010、UIR-ST-012、UIR-ST-013、UIR-ST-016 | TASK-009、TASK-010、TASK-012、TASK-013、TASK-015 | TCOV-008、TCOV-010、TCOV-012、TCOV-015、TCOV-016 | EVD-008、EVD-010、EVD-012、EVD-015、EVD-016 | passed / 已通过 |
| GOAL-004 | NFR-005 历史兼容与不可变 | AC-014、AC-015 | ARC-008、ARC-010；ADR-002 | UIR-ST-003、UIR-ST-012、UIR-ST-013 | TASK-003、TASK-012、TASK-013 | TCOV-014、TCOV-015 | EVD-014、EVD-015 | passed / 已通过 |
| GOAL-005 | NFR-006 安全与隐私 | AC-002、AC-004、AC-012、AC-014 | ARC-001、ARC-002、ARC-006、ARC-007、ARC-010 | UIR-ST-001、UIR-ST-002、UIR-ST-004、UIR-ST-008、UIR-ST-009、UIR-ST-010 | TASK-001、TASK-003、TASK-004、TASK-008、TASK-009、TASK-010 | TCOV-002、TCOV-004、TCOV-012 | EVD-002、EVD-004、EVD-012 | passed / 已通过 |
| GOAL-005 | NFR-007 依赖与可移植性 | AC-018 | ADR-009 | UIR-ST-001、UIR-ST-015 | TASK-001、TASK-002、TASK-014 | TCOV-018 | EVD-018 | passed / 已通过 |
| GOAL-005 | NFR-008 可维护性 | AC-002、AC-018 | ARC-001、ARC-002、ARC-003、ARC-004、ARC-005、ARC-006、ARC-007、ARC-008、ARC-009、ARC-010；ADR-009 | UIR-ST-001、UIR-ST-011、UIR-ST-015、UIR-ST-016 | TASK-001、TASK-011、TASK-014、TASK-015 | TCOV-002、TCOV-011、TCOV-018 | EVD-002、EVD-018 | passed / 已通过 |

## 完整性门禁

- 每个 FR、BR、NFR 至少映射一个 AC、架构机制、Story、Task、TCOV 和 EVD；
- 每个 AC-001～018 至少出现在一个需求行；
- 每个 UIR-ST-001～016 均在 Phase/Story 包中定义；
- 每个 TASK-001～015 均在 Development Plan 中定义；
- 每个 TCOV-001～018 和 EVD-001～018 均在 Test Plan 中定义；
- 任何实现、测试或正式迁移后必须重算 RTM 状态，不能手工把 `planned` 改为通过。

## 当前 EVD 逐项登记

| EVD | 证据类别 | 当前结论 | 状态 |
|---|---|---|---|
| EVD-001 | 全局回归与正式 manifest 验证 | 安装时 241 项；本轮发布前当前树 234 项；A/B 附件集合有效 | passed |
| EVD-002 | 作用域扫描 | 全局包无天津路径、case ID 和项目定位器 | passed |
| EVD-003 | Test Data 与身份 | A/B 独立数据源及 hash 一致 | passed |
| EVD-004 | 参数清单/renderer | Human、Midscene、Resolved、Playwright 同源 | passed |
| EVD-005 | Sync | dry-run/apply、计划绑定、CAS、readback 通过 | passed |
| EVD-006 | Execution Guard | 三个门禁点和业务写保护通过 | passed |
| EVD-007 | Runtime 影响 | 仅被引用且展开值影响 build | passed |
| EVD-008 | 每日历史 | 按日 JSONL 与无事件不建文件通过 | passed |
| EVD-009 | 日志完整性 | 逐行 JSON、hash、index、锁门禁通过 | passed |
| EVD-010 | 修复关闭 | unfinished 投影可重建且当前为空 | passed |
| EVD-011 | 正式编译身份 | A/B/product active 为 valid/in_sync/ready | passed |
| EVD-012 | 运行证据链 | A/B RunResult v3 与 resolved snapshot/evidence 绑定 | passed |
| EVD-013 | 恢复与幂等 | 故障注入和重试语义回归通过 | passed |
| EVD-014 | 历史不可变 | 336 个历史文件 hash 未变化 | passed |
| EVD-015 | 正式迁移 | r21 后继部署及产品 aggregate 通过 | passed |
| EVD-016 | 精确清理 | 21 个 cache/IDE 目录清理；保护对象零删除 | passed |
| EVD-017 | 真实业务验收 | A/B 各一次 canonical 成功 Run，submit_count=1 | passed |
| EVD-018 | 供应链与敏感边界 | 依赖清单、许可证、作用域和敏感扫描通过 | passed |

## 当前完整性门禁

- FR-001～FR-014、BR-001～BR-005、NFR-001～NFR-008 均有独立需求行；
- AC-001～AC-018、TASK-001～TASK-015、TCOV-001～TCOV-018、EVD-001～EVD-018 均已显式登记；
- 开放 P0/P1、未映射动作、风险接受和未完成修复项均为 0；
- 当前文档版本关系由 `current-artifacts.json` 和规范 Envelope 管理。
