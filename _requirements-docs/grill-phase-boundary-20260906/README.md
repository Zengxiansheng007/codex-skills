# Grill 阶段隔离文档

**当前状态：代码实现、全局安装和 GitHub 发布已完成。本目录是复核后的公开文档 v1.0。**

代码基线：[b4fa506](https://github.com/Zengxiansheng007/codex-skills/commit/b4fa50611f2f4c627903df2cc439ff483ce6cfc6)。本次文档提交补齐交付说明及说明文件修正，未修改运行时Python、JSON Schema或HTML夹具。

## 阅读顺序

| 文档 | 内容 |
| --- | --- |
| [需求与RTM](requirements-prd-v1.0.md) | 已确认的13项需求、验收条件及当前覆盖 |
| [实际架构](architecture-v1.0.md) | V2状态、字段、职责及真实接口 |
| [使用流程](usage-v1.0.md) | 公开命令、初始化约束、回写顺序与异常 |
| [开发完成记录](development-plan-v1.0.md) | 三个Story的实际执行与交付 |
| [测试计划及结果](test-plan-and-results-v1.0.md) | 34个函数、独立QA、前向验证与跳过说明 |
| [验收与发布](acceptance-release-v1.0.md) | 69文件候选与71文件代码发布的区别、安装和GitHub验证 |
| [使用复盘](retrospective-v1.0.md) | 已修复问题与全局框架后续事项 |
| [本次文档复核](document-review-v1.0.md) | 旧稿过期/不一致项及修正依据 |
| [公开证据摘要](evidence-summary.json) | 从实际证据提取的计数、案例、来源哈希与能力边界 |
| [文档文件清单](document-manifest.json) | 文档与证据摘要的内容哈希 |

## 关联Skill

[grill-system](../../skills/grill-system/SKILL.md) · [write-prd](../../skills/write-prd/SKILL.md) · [write-requirements-prd](../../skills/write-requirements-prd/SKILL.md) · [domain-modeling](../../skills/domain-modeling/SKILL.md)

原始v0.1需求/计划/候选报告作为阶段历史保留，未将“当时尚未实现”改写为“当时已完成”。这里提供当前状态的独立整理，不公开原始任务、模型输出、审批或PowerShell审计日志及本机路径。

能力范围是Skill局部流程与证据检查。它不提供全局文件拦截；外部变化的语义由主控或用户判断。文件符号链接用例因测试主机权限跳过，实际Windows目录联接拒绝已验证。

