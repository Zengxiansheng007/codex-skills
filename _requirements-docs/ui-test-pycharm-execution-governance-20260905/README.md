# UI-Test PyCharm 执行治理发布回顾

版本：1.0.0；回顾日期：2026-09-05。发布授权来自本次用户明确请求；它不改写此前排除发布的实现需求锚点，也不扩大到 GitBook。

## 本次发布范围

通用 `skills/ui-test` 与本目录的脱敏回顾文档。通用包包含 PyCharm 来源识别、唯一 Run ID、项目串行锁、事务化 finalization、版本迁移和验收证据校验。项目 adapter 的城市目录恢复仅在文档中说明机制，项目源码及配置不公开。

不发布：项目 adapter、正式运行目录、运行截图、原始日志、业务值、私有地址、账户信息、私有索引、安装备份、Claude handoff 或执行产物。其他 Skills 不在本次变更范围内。没有 GitBook 同步、生产操作、真实 UI 重跑或数据清理。

## 当前结论

- 实现及部署：候选验证、安装后复验、A/B 零提交 qualification、CAS activation 和正式读回均有本地证据。
- 人工业务验收：用户确认通过；本地 A/B 记录均为 PyCharm 来源、一次提交且业务写入验证成功，pytest session 状态为 0。
- 整体完成：仍为 `functional-accepted / repair-needed`，不得将本次 GitHub 发布解释为 `completed`。外部 helper 进程退出证据与 AcceptanceResult 尚缺；实际人工顺序为 B、B、A，与原“先 A 后 B、各一次”计划不一致，需要验收评审处理，不通过重复创建补证。
- 城市恢复覆盖：A/B 零提交现场的目录首次即就绪，恢复次数均为 0。故障恢复分支由离线测试覆盖，不能宣称真实故障恢复已被这两次 qualification 验证。

代码发布、业务验收和整体完成是独立状态；历史失败及已生成业务数据保持不变。

## 文档

- [根因、架构与恢复机制](architecture-and-repair.md)
- [验证、追踪与未关闭门禁](validation-and-rtm.md)
- `review-result.json`：由文件哈希、既有测试清单和发布基线读回生成的脱敏索引。
- `document-manifests.json`：内容摘要与文档发布状态；GitHub 推送结果单独留存于本地发布证据，不自证整体验收。

本目录是已授权实现的发布回顾，不是新的业务需求批准、部署许可或项目执行配置。
