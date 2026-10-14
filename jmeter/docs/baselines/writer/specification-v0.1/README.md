> 公开投影：业务规则与原编号保留；“本轮”指源文档编写阶段。源哈希、路径适配与当前发布范围见 jmeter/docs/publication-context.md 及导出清单。

# jmeter-tps-writer 规格包 v0.1

日期：2026-10-13。独立 to-spec 产物。当前仅完成规格编写和文档核对，没有产品实现、真实 JMeter 测试、安装、发布或流程状态更新。

| 阅读顺序 | 内容 |
|---|---|
| [1. 主规格](spec.md) | 问题、方案、40 条故事、技术决定、测试边界与排除项 |
| [2. 接口与数据契约](interfaces.md) | writer / runner 公开入口、输入、认证角色、CSV、两类副本与分层结果 |
| [3. 改动范围](change-scope.md) | 候选基线、writer 新模块、runner 必要写集、保持模块与开发顺序 |
| [4. 测试方案](test-plan.md) | 资格门、入口行为用例、关联回归、真 JMeter / WorkBuddy 与 AC 覆盖 |

## 已固定的范围

writer 编写和短验证；runner 独立正式寻峰。默认业务断言 success=true；已有缺断言仅提醒。短验证 1 / 0 / 1，单账号 CSV 隔离仅改验证副本引用。认证 JSON→CSV，JMeter 原生分配；正式每轮准备全部配置账号。失败不自动修正或重试；不新增专门整体超时/进程树模块。

## 当前确认与未验证

- 核心需求依据：[需求 v1.1](../requirements-v1.1.md) 与已有 Q1–Q22 答复。SHA256：82068B0AD6D21BA6E59C9D065394F78F8B209D1B07BAAD1D0B4BEA43C5115D18。
- 用户本轮明确确认：“采用入口行为测试＋受控 JMeter 集成（推荐）”。后续实际发压仍需要具体任务范围授权。
- 原型：Logic HTML（历史本地参考，未随本次导出）。它仅做模拟，不能证明本规格技术选择可执行。
- 整份需求 v1.1、普通编写建议与当前规格仍未整份确认。进入 to-spec 是细化授权，没有追溯改写需求状态。
- 本地候选与 5.6.3 随包文档已只读核对。原生解析、固定认证模板、文件/属性基准和新消费者行为仍需 G-01–03 真实资格验证。
- 第二台环境暂无，未测试。没有任何产品 AC 被标为 passed。

新增技术选择均作为可审阅方案：本地原生解析适配、认证前/后处理模板、进程内 Cookie 属性绑定、按执行 JMX 名隔离本轮产物、只读 check-input、缺正式线程字段时的 1 线程结构占位。它们不自动成为历史用户决定或已验收机制。

## 读取的官方本地材料

来自本机已有 apache-jmeter-5.6.3 发行包，未运行 JMeter 命令、未安装依赖、未使用外部检索服务。

- bin/saveservice.properties：SetupThreadGroup、JSR223PreProcessor / PostProcessor、CSVDataSet、JSONPostProcessor / JSONPathAssertion 等保存名称。正式实现还需回读实际序列化产物。
- docs/api/org/apache/jmeter/protocol/http/curl/BasicCurlParser.html 与 Request 文档：公开解析和请求字段；不等于官方无头转换器。
- docs/api/org/apache/jmeter/services/FileServer.html：执行计划基准、脚本名与文件解析 API；不等于本方案属性/迁移机制已实测。
- docs/api/org/apache/jmeter/threads/AbstractThreadGroup.html、JMeterVariables.html 与 control/LoopController.html：线程组、控制器与迭代数 API。
- docs/api/org/apache/jmeter/samplers/SampleResult.html：样本错误/停止标志；不新增 OS 进程控制方案。
- 现有需求研究说明：setUp 顺序、CSV 主迭代、JSON 提取与断言、1 秒不是墙钟上限。

## 发布状态

本任务没有提供 writer 对应的 Issue tracker 目的地与 triage 标签配置，当前规格未发布，也没有打 ready-for-agent 标签。

读取的 to-spec Skill（历史本地参考，未随本次导出） 明确要求：
> Do not assume GitHub or create a remote tracker without authorization.

如需发布，可用 setup-matt-pocock-skills 配置项目 tracker 和标签后，明确本任务目的地；不自动套用历史 runner 的 GitHub 发布授权或其他专项 tracker。

## 执行来源

Skill：to-spec。实际路径 <LOCAL_PATH>
SHA256：990F1873335D98B569D6BB011AE9F28BD2F842F5F7B35C3B5D95D1AA0A04FD15。
按 Codex 统一执行协议在流程外独立执行，未创建 develop-system 帧、ticket 或执行台账。

技术资格门未关闭前，不把自动认证兼容标记完成。进入开发时绑定本规格的准确版本/写集，不以“规格文件齐全”替代开发、资格或软件验收。

