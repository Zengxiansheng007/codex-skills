---
artifact:
  id: ART-GRILL-DOCREVIEW-PUBLIC-001
  type: review
  version: 1.0.0
  statusCode: approved
  statusLabelZh: 已批准
  owner: Codex
  sourceBaseline:
    codeCommit: b4fa50611f2f4c627903df2cc439ff483ce6cfc6
  approvalBasis: reviewed-document publication requested by user; approved product
    rules unchanged
---
# 文档复核记录 v1.0

本轮按用户“回顾文档，调整后一同推送至github”的指令进行。产品规则和运行时代码不变；原始需求/计划/验收/复盘及原始运行证据保持历史原件。

| 原文问题 | 修正 |
| --- | --- |
| 需求RTM、开发计划仍写未实现或只准备ST-001 | 新公开版说明三Story及FR/AC已完成声明范围内验证 |
| 候选报告/复盘仍写未安装、未发布 | 新当前状态文档关联已完成安装及b4fa506代码发布；不修改当时的历史事实 |
| 架构遗漏blocked，混用status/phase/result及closure字段 | 对照实际Schema列出八个phase、八个result和closureEvidence |
| 规划稿描述不存在的三态artifact-check接口 | 改为helper的实际路径/快照/范围/后置函数和runtime语义门槛 |
| 旧计划的Claude轮数/时限被读成产品限制 | 标为历史执行提案，说明本任务授权改用Codex子Agent |
| 将准备检查或AC数量当成测试数量 | 区分34函数、独立QA16通过+1跳过、43文档检查和80准备检查 |
| Skill命令清单漏validate，正式门槛仍只指V1 Schema | 补齐实际17命令，并将V2与旧报告检查说明分开 |
| expectedSha256文案声称支持大小写 | 明确使用小写值；当前代码精确比较，不自动转换 |
| validated分类条目还写Pending | 将初始说明标为历史，并补上已发布验证状态 |
| 原始证据包含机器路径/模型或审计记录 | 仅发布选定字段的证据摘要及来源哈希，所有公开引用可在仓库解析 |

## 本轮验证

文档核对使用已发布源码、原始验收与发布结果，另有只读子Agent复核。发布前检查Markdown链接、FR/AC完整性、17命令及枚举一致性、测试计数、隐私边界、四个Skill结构/记录，并确认所有非Markdown源码字节保持不变。

本轮不会重复运行已经通过且代码未变的产品测试，也不会把文档检查说成新的产品实测。

## 公开与本地的分界

公开：本目录的当前文档、整理后的证据摘要及文档文件哈希；相应Skill Markdown说明和变更记录。
本地：历史PRD/计划、完整模型/任务/审批/审计日志、原始测试工作目录、备份位置及含本机路径的回执。

代码发布基线固定为b4fa50611f2f4c627903df2cc439ff483ce6cfc6。本轮文档有独立提交；不把此前GitHub适配器的commit reused字段解释成当前文档已在旧提交中存在。

