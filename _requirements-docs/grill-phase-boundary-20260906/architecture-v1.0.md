---
artifact:
  id: ART-GRILL-ARCH-PUBLIC-001
  type: architecture
  version: 1.0.0
  statusCode: approved
  statusLabelZh: 已批准
  owner: architect
  sourceBaseline: b4fa50611f2f4c627903df2cc439ff483ce6cfc6
---

# Grill 实际架构 v1.0

本文件对照已发布代码记录实际结构，替代原规划文档在当前使用中的地位，不改变已确认需求。

## 职责边界

| 组件 | 作用 |
| --- | --- |
| ARC-001：grill-system 会话层 | 单台账、单题记录、整场关闭、例外和恢复 |
| ARC-002：grill_session_runtime.py | CLI及语义门槛、计划冻结、实际后置验证、报告投影 |
| ARC-003：grill_artifact_checks.py | 路径规范化、reparse检查、保护集合快照/差异、范围判断及文件哈希核对 |
| ARC-004：文档Skill | 正式内容合并；Grill内的领域建模仅返回候选决定 |
| ARC-005：主控 | 解释实际用户确认、核对语义变化、审查实际证据与决定后续行动 |

资产helper没有规划稿中的“allowed/blocked/review-needed”三态操作API。回写资格由runtime命令与语义检查判断；helper通过返回快照/差异或抛出边界错误提供事实。

## V2协议

schemaVersion为2.0。phase与result分开；V1的status仅属于旧报告检查。

| phase | 含义 |
| --- | --- |
| grilling | 评审中 |
| awaiting-closure | 等待整场结束确认的评审阶段 |
| review-ended | 已有整场关闭记录 |
| writeback | 已建立回写批次 |
| writeback-complete | 后置条件验证完成 |
| paused | 暂停，保留恢复点 |
| repair-needed | 需要修复或完成失败核对 |
| blocked | 阻塞 |

result取值：in-progress、ready-for-writeback、conclusions-only、completed、partial-failure、blocked、repair-needed、legacy-read-only。不能把result=completed解释成已部署或全局防写。

主要字段为ledgerPath、workspaceRoot、questions、decisions、effectiveDecisions、evidenceIndex、openItems、sourceBaseline、protectedAssets、processArtifacts、closureEvidence、writebackPolicy、exceptions、recovery、checkpoints、writebackReceipts。实际结构以[V2 Schema](../../skills/grill-system/schemas/grill-session-v2.schema.json)和[会话契约](../../skills/grill-system/references/grill-session-contract.md)为准。Schema检查顶层结构/枚举等，运行时进一步检查语义与路径；不能只用Schema通过来判断能否写正式文件。

## 关键决策

- ADR-001：phase/result独立，单题回答不生成closureEvidence；没有关闭依据的手改phase路径被拒绝。
- ADR-002：新版写入流程与旧报告检查分开。V1仍可检查，不自动迁移或补造结束授权。
- ADR-003：保护集合使用规范化路径与内容快照。Windows reparse属性在解析、遍历和读取前检查；不创建OS锁或ACL。
- ADR-004：批次冻结完整有效决定、批准范围和目标后置哈希。公开计划生成器统一绝对/相对路径，并拒绝同一目标的重复别名。
- ADR-005：只验证下游合并结果，不承担通用PRD编辑器职责。无变化记录no-op；真实更新记录updated；部分失败记录partial-failure。
- ADR-006：V2使用环境中已安装的jsonschema。缺失时报告jsonschema-unavailable并阻塞相应校验，不静默换成不完整校验器或安装依赖。

## 异常与恢复

未决P0不能通过普通关闭/回写门槛；风险接受需要具体条目、依据、范围和接受方。普通台账更新不被误当成正式资产写入，允许继续回答问题。

外部变化先记录路径/哈希差异。格式变化只能经显式reviewer证据走reconcile-format-only；语义冲突按受影响问题重开。一次例外需create/consume/finish完整链路，实际后置条件核对后恢复正常评审。

关闭记录的statement/source/recordedAt由主控依据实际用户输入提供。运行时检查必要结构和状态，不提供用户身份签名或自然语言确认真实性证明。任意工具直接绕过此流程的写入无法被它预先阻止；两个检查点间写后恢复也不能只靠首尾哈希排除。

