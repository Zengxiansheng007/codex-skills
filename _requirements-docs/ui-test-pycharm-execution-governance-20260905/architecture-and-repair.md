# 根因、架构与恢复机制

版本：1.0.0。追踪：UIT-PYCHARM-GOV-20260903；UIT-PYCHARM-FINALIZATION-ST013-20260904；CR-20260904-001、CR-20260904-002。

## 根因回顾

最初正式 PyCharm 入口缺少显式 Run ID，项目运行时没有消费统一解析结果，因而在 setup 阶段拒绝执行。单元测试、收集、release 验证和零提交 qualification 的通过并不能证明 IDE 的完整业务调用链通过。

来源识别还受到 JetBrains helper 改写 argv、主模块路径以及本地 TeamCity 协议标记影响。修复从真实 runner 入口证据分类来源，但来源分类与 R2 批准仍分离，环境标记本身不授予权限。

后续确认的 finalization 根因是自定义 pluggy hook 使用 keyword-only 参数，导致 hook 参数名为空，真实分发出现 TypeError；直接调用函数的测试绕过了这个分发差异。更深层缺陷是 passed terminal 早于 finalizer 落盘，造成业务/terminal 已通过而 IDE 进程失败。

## 控制面与版本

| 组件 | 责任与边界 |
|---|---|
| 通用 pytest 插件 | 每个 node 生成唯一上下文、Run ID、attempt；项目 runtime 只消费上下文 |
| 来源解析与批准 | PyCharm 的普通 Run/Rerun/Debug 在 test/R2、stable-active、2.2 策略、锁等门禁满足时获当前 node 批准；CLI 仍需显式参数 |
| 项目锁 | 按项目组、产品、环境跨进程非阻塞串行；xdist/冲突在 BrowserContext 前拒绝 |
| 新契约 | Project Config 2.2、ExecutionContextV3、AttemptV2、RunResultV5、transaction-v1 |
| 历史契约 | 2.1/V2/V1/V4 及更早版本保留审计读取，不获得新执行或验收资格 |
| 外部验收 | 原 helper 进程退出证据与 SessionResult、授权、事务闭包一起校验；RunResult 不自证人工通过 |

普通业务执行的完成顺序为：最终 teardown report → finalization candidate → 内容寻址 RunResult/evidence 对象 → 单一原子 commit manifest → receipt → 唯一 terminal → SessionResult → 外部 AcceptanceResult。

任何缺失、非零退出或 post-run 恢复都不得被追认为原进程通过。qualification 使用独立 QualificationResult，保留 attempt/terminal，但不生成业务 commit/receipt，不消费提交许可。

## 项目城市目录恢复

项目侧曾在目录探测失败后直接重载创建 URL。经用户授权，adapter 1.4.1 改为关闭浮层、进入同主机公告管理列表、等待就绪、通过已有 Page Object 实际点击创建，再探测目录。

只有未开始填写、尚未提交、未恢复过的操作实例可以恢复一次；第二次目录失败或列表/创建入口失败即停止。已填值后不导航离开，不丢弃表单后重新提交。各阶段截图和哈希保存在项目侧，成功快照仍记录首次失败与恢复路径。

这修复的是测试资产的恢复机制；已有失败证据不足以断言城市后端故障或前端初始化就是唯一根因。该 adapter 不属于通用 Skill，本次不把项目源码、配置或运行证据发布到公开仓库。
