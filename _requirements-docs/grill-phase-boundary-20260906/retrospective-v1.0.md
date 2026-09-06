---
artifact:
  id: ART-GRILL-RETRO-PUBLIC-001
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
# 开发系统使用复盘 v1.0

本次四个Skill的改造、验收、全局安装与GitHub代码发布均已完成。原复盘的“全局发布未执行”属于候选完成时的阶段快照，不再作为当前状态。

## 有效做法

已确认需求与实际实现分开保存，使执行者从Claude切换到Codex子Agent时无需重开产品规则。运行时、文档、独立QA与前向测试按文件所有权分工；GPT-6主控复核实际差异和证据，子Agent声明不决定整体完成。

单台账与正文边界落实到文档、Schema、CLI及下游规则。独立CLI正常路径和对抗测试发现了库级自测未覆盖的问题；真实Agent使用又暴露了公共接口缺失。

## 问题与结果

| 等级 | 问题 | 当前处置 |
| --- | --- | --- |
| P1 | 执行CLI不支持反馈Schema所声明方言 | 任务局部采用受核对的兼容副本和原Schema后验；未全局改适配器 |
| P1 | 外层成功状态可能掩盖子进程失败 | 本任务显式检查内层退出证据；全局runner改进仍是独立事项 |
| P1 | 外部执行服务限流 | 保留失败记录；经用户明确授权改用Codex子Agent |
| P0 | 缺少关闭/P0依据仍能推进 | 已修复并回归 |
| P0 | Windows目录联接未被正确拒绝 | 已按reparse属性处理，真实用例通过 |
| P1 | 普通台账更新被正式写入门槛过度阻断 | 已分离校验，CLI正常链路通过 |
| P1 | no-op与真实合并混淆 | 明确outcome和实际变化字段 |
| P1 | 公共计划生成/消费路径不一致 | 统一规范化，绝对路径及重复别名回归通过 |
| P2 | 下一问题/计划指纹需要手工拼装 | 增加公共命令及明确输入说明 |
| P2 | 本机文件符号链接能力不足 | 保留跳过；未提权，不夸大覆盖 |
| P2 | 发布文档残留本机路径 | CR-006已适配；本轮补齐公开交付文档 |

## 文档维护教训

“执行前计划”“候选完成”“已安装”“已公开发布”必须带阶段和基线，避免旧快照被当作当前状态。验证计数需区分函数、场景、准备检查和AC映射。分类台账中的初始Pending说明应保留为历史，并提供当前完成状态，而不是一边标validated一边仍呈现待验证。

全局适配器方言能力预检、退出传播和通用执行者选择策略仍可另行改进；它们没有被包装为本次已修复的全局组件，也不阻碍已完成的Grill范围交付。

[当前验收发布](acceptance-release-v1.0.md) · [本次文档复核](document-review-v1.0.md)

