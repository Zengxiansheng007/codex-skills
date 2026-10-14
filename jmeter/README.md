# JMeter Skills

独立维护 JMeter 脚本编写、短验证和正式寻峰的源码与文档。

| 内容 | 位置 | 当前状态 |
|---|---|---|
| jmeter-tps-runner · WorkBuddy | [skills/jmeter-tps-runner](skills/jmeter-tps-runner/SKILL.md) | 归档现有 0.3.0 候选源码，保持原清单；不等于本轮联合功能开发或发行验收完成 |
| jmeter-tps-writer | [开发状态](skills/jmeter-tps-writer/README.md) | 尚未实现，没有可安装 SKILL.md |
| writer / runner 联合规格 | [规格入口](docs/joint-spec-v0.1/README.md) | 57故事，原32组需求/AC，8工作包，80项计划用例；新增产品测试未执行 |
| 本次提交和基线差异 | [发布上下文](docs/publication-context.md)、[文档回顾](docs/document-review.md)、[导出清单](docs/export-manifest.json) | 来源/公开投影/候选/未验证范围分开记录 |

## 职责

writer 从 cURL 编写 JMX，处理需要的 JSON Cookie→CSV，并逐目标按业务 **1线程、Ramp-up 0、持续1秒**验证；正式原件和原始数据保留。runner 独立确认负载/门槛后逐 HTTP 寻峰，指标来自官方 report。

联合计划新增固定输出根/强制目录准备、采样后独立官方报告、十分钟单次监控提醒及用户决定的报告专用停止。**这些是待开发能力，现有 0.3.0 候选未实现。**不要依据规格中的拟定入口运行旧包或宣称已支持。

## 版本与使用边界

现有 WorkBuddy 候选的包和资源在 `skills/jmeter-tps-runner/` 内。阅读其真实 SKILL.md 及宿主/输入要求；执行需要当次明确目标、许可、JMeter入口、负载和门槛，不能执行文档示例或历史业务脚本。源码归档不新增真实压测授权。

本次没有改产品代码或重新验证其运行行为，没有生成安装发行包、操作 WorkBuddy 或运行 JMeter。旧候选的资格限制保持；正式导入/触发/停用、Java/宿主证据及第二环境按当前实际证据核验。

已有 [Codex 版本源码](../skills/jmeter-tps-runner/SKILL.md) 与 [历史文档](../_requirements-docs/jmeter-tps-runner/README.md) 保持原位。这里的 WorkBuddy 候选与旧 Codex 版本分别维护，不把旧证据转记到新功能。
