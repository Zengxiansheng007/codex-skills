---
artifact:
  id: ART-GRILL-USAGE-PUBLIC-001
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
# 使用流程与公开接口 v1.0

以下说明面向Skill执行者，不把示例当成真实用户授权。正式文档内容仍由对应文档Skill合并。

## 初始化

使用已安装的Python及jsonschema；不自动安装依赖。从仓库根使用下面的相对脚本路径，安装环境则解析实际Skill根路径：

~~~text
python skills/grill-system/scripts/grill_session_runtime.py init --session .grill/session.json --session-id GRILL-EXAMPLE-001 --scenario requirements --workspace-root .
~~~

先创建会话父目录。初始化不会覆盖已有文件。主控在开始评审前补齐实际问题来源、protectedAssets、writebackPolicy.approvedScopes及processArtifacts；保留init生成的身份和规范化路径。ledger路径不得与正式资产重叠。formal目录是示例名称，不是固定产品目录。

recordMode=conversation-only的init将数据输出到标准输出并声明persisted=false，不创建ledger文件；后续对话内状态由调用方维护，不能宣称具有磁盘恢复能力。

## 17个命令

| 命令 | 用途 |
| --- | --- |
| init | 创建不覆盖现有文件的会话，或输出不落盘状态 |
| validate | 按read/close/write意图做结构及语义检查 |
| propose-question | 从question-json追加下一题，检查唯一ID及单个proposed问题 |
| record-answer | 记录回答、同步关联P0未决项及有效决定 |
| close | 记录整场关闭依据，选择默认回写/仅留结论策略 |
| pause | 保存恢复点 |
| resume | 恢复既有阶段，不新授予权限 |
| reopen | 带原因及新证据重开相关问题，保留被替代决定 |
| checkpoint | 观测受保护资产及哈希 |
| reconcile-format-only | 记录有reviewer依据的格式变化协调 |
| create-exception | 登记一次、限定范围的中途例外 |
| consume-exception | 消费例外并进入等待后置验证状态 |
| finish-exception | 核对实际变化/哈希并建立新基线 |
| prepare-writeback-plan | 生成公开、可直接消费的规范化计划与指纹 |
| begin-writeback | 使用plan建立允许的下游批次 |
| verify-writeback | 核对实际内容、完整变化集与冻结计划 |
| render-report | 从结束后的权威台账生成HTML |

validate成功只是对应意图的校验结果，不是通用文件写入权限，也不等于已做全部快照比较。实际回写仍须经过begin-writeback和verify-writeback。

## 逐题评审

question-json对象至少含id、question、purpose、recommendedAnswer、blockingDecision、severity；evidence可为引用数组。propose-question会为P0题同步openItems。用户回答后调用record-answer，正式正文、元数据和替代版本保持冻结。没有新证据或缺口时不重问已确认内容。

## 整场结束后的批次

1. 主控依据用户的整场结束指令准备closureEvidence。示例字段statement、source、recordedAt必须填写实际记录，不复制虚构确认。
2. close按既定范围沿用默认回写授权；conclusions-only或deferred只交付结论，不进行正式合并。
3. 复核已评审基线及当前内容，必要时处理外部变化；不得把新取快照自动当成用户已接受变化。
4. 将计划输出路径预先登记在processArtifacts，kind为writeback-plan；报告路径登记为report。
5. 准备目标后置条件：items数组中每项有id、path、expectedSha256。expectedSha256使用hashlib.hexdigest形式的小写64位十六进制；当前实现按字符串精确比较，不自动统一大小写。
6. 调用prepare-writeback-plan生成规范化计划。绝对路径可作为输入，输出以工作区相对路径表示；不要重新实现私有指纹算法。
7. begin-writeback成功后，由文档Skill执行本批次的正式合并，再将冻结计划的items用于verify-writeback。
8. 根据回执区分updated、no-op及partial-failure；无变化不制造版本，失败不能宣称合并完成。最后从台账生成并校验报告。

~~~text
python skills/grill-system/scripts/grill_session_runtime.py prepare-writeback-plan --session .grill/session.json --items .grill/items.json --output .grill/plan.json
python skills/grill-system/scripts/grill_session_runtime.py begin-writeback --session .grill/session.json --workspace-root . --batch-id B-001 --checkpoint-id CP-001 --plan .grill/plan.json
python skills/grill-system/scripts/grill_session_runtime.py verify-writeback --session .grill/session.json --workspace-root . --receipt .grill/receipt.json
~~~

这些命令假定实际确认、范围、检查点及输入文件已经正确建立；它们不自动完成内容合并或代替用户作决定。完整输入约定见[阶段契约](../../skills/grill-system/references/phase-boundary-contract.md)。

