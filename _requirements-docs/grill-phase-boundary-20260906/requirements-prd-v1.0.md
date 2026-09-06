---
artifact:
  id: ART-GRILL-PHASE-PUBLIC-001
  type: prd
  version: 1.0.0
  statusCode: approved
  statusLabelZh: 已批准
  owner: product-requirement
  sourceBaseline:
    codeCommit: b4fa50611f2f4c627903df2cc439ff483ce6cfc6
  approvalBasis: reviewed-document publication requested by user; approved product
    rules unchanged
---

# Grill 阶段隔离需求 v1.0

本文件是已确认需求的公开整理版。原v0.1仍作为评审阶段历史保留；本次没有新增或修改产品规则。实现、全局安装和代码发布已完成，代码基线为上述提交。

## 目标与范围

评审期间只积累决定，正式资产整份冻结；用户确认整场结束后默认集中回写，不重复索要同一回写授权。明确仅保留结论时不回写。适用全部七种Grill路由及对应文档调用方，保护PRD、RTM、架构/测试文档、术语表、ADR和替代版本。

角色：用户决定取舍及整场结束；grill-system拥有评审台账和局部门槛；对应文档Skill拥有正式内容合并；主控负责独立验证。开发执行者的选择不改变产品需求。

## 已确认规则

“单题已确认”表示用户接受该问题的决定；“评审结束”表示结束条件满足并有用户针对整场评审的确认；“已合并”表示相应决定已经写入目标文档并完成对应验证。三者不能互相推断。

概念阶段为：评审中 → 待结束确认 → 评审已结束 → 集中回写 → 回写完成。暂停、证据不足、待修复属于明确的非成功分支。具体字段名由实现阶段确定，但不得把单一 complete 字段同时解释为评审结束、文档批准、已合并和实现完成。

BR-001：当前明确用户指令优先；单题“确认”、普通“继续”、超时、无回复、退出工具、报告校验通过均不能单独触发整场结束。
BR-002：结束确认沿用既有集中回写授权，不额外重复索要同一授权；“结束并只保留结论”“暂不回写”时仅返回结果。
BR-003：未决 P0 阻止正常完成；显式风险接受必须带具体风险、接受依据、影响范围和剩余验证职责，不能作为通用跳过校验的许可。停止交互不自动等于成功结束。
BR-004：最终 HTML 是台账的展示投影，不是第二份可独立修改的决定来源。报告不能覆盖 PRD，PRD 不能覆盖架构或实施计划等不同职责资产。
BR-005：参考资料仅提供可选择的证据。Spec Kit 的逐题合并/保存/完整校验与本地约定不兼容，不得因引用该项目而继承；不照搬固定五题上限、提交命令或其他外部执行动作。
BR-006：风险或失效状态可先记录在台账并阻止下游使用；无需为表达“正在评审、冲突、待重开”而修改冻结的文档头部。

## 功能需求

| ID | 优先级 | 需求 |
| --- | --- | --- |
| FR-001 | P0 | 显式区分问题确认、整场结束和集中回写；持有用户结束依据及有效授权范围后才进入回写，沿用默认授权并处理仅留结论指令 |
| FR-002 | P0 | 所有现有路由及嵌套调用继承评审写入边界；被调用 Skill 返回证据或候选决定，不立即修改正式资产 |
| FR-003 | P1 | 每场评审维护一份权威结构化台账，逐题只更新必要字段；报告、正式影响记录、完整校验不逐题成套生成 |
| FR-004 | P0 | 明确受保护资产集合，整份冻结正文和元数据，同时禁止以逐题新建替代版本规避；会话使用限制不写入正式正文 |
| FR-005 | P0 | 按有效结果条件恢复文档编写；blocked、repair-needed 或缺失结束依据不得因调用返回而自动回写；风险接受按范围单独判断 |
| FR-006 | P0 | 中途写入仅执行用户明确的一次范围授权，记录授权来源、对象、实际差异、必要校验和新基线，完成后恢复冻结 |
| FR-007 | P0 | 回写前复核基线；发现外部变化先保留并核对。无语义影响且仍在原范围内可继续；有影响只重开关联问题，不覆盖外部改动 |
| FR-008 | P1 | 暂停/恢复时携带阶段、基线、决定、未决项、例外与下一题；不重复已确认问题，不把恢复动作当作新回写授权 |
| FR-009 | P0 | 按最终有效决定集中合并并集中校验；无实际变化不升版，重复执行不重复合并；部分失败记录已完成/待处理范围，不宣称成功 |
| FR-010 | P1 | 在基线选择及适配说明中明示采纳和排除的规则，确保逐题保存、立即更新术语等外部规则不重新覆盖本地阶段约束 |
| FR-011 | P0 | 校验同时覆盖会话语义、结果映射和实际文件变化证据；禁止把字段齐全或退出码零当作完整边界验证；保留未验证范围 |
| FR-012 | P1 | 保留旧报告与版本，不补造历史结束授权；旧会话缺失信息保持未知，不允许静默当作已授权回写；兼容策略在实现中可验证 |
| FR-013 | P1 | 只询问影响范围、验收或取舍的真实缺口；已确认内容不重复提问；重开时说明新证据/冲突并关联原决定，不覆盖历史 |

## 数据与非功能要求

权威台账至少表达：sessionId、场景、当前阶段、评审对象和基线、允许写入的过程文件、受保护资产、问题及用户回答、有效与被替代决定、证据引用、未决项、结束依据、回写策略/范围、例外、回写结果和恢复点。此为语义要求，不预设新 Schema 的具体字段拼写。

问题 ID 在同一会话内唯一，跨会话必须与 sessionId 联用；决定可追踪到具体问题或用户直接指令；没有消息 ID 时可记录可核对的对话摘录，不伪造消息 ID 和时间。基线至少可识别文件路径和内容版本/指纹；没有既有文档时记录“尚未创建”，不能伪装成已有基线。

NFR-001：可追踪性——所有需求、决定、验收项和证据引用可解析；实际测试未执行时明确标记计划，不能使用参考文档代替运行证据。
NFR-002：交互成本——逐题产生一次必要台账更新，正式 PRD 版本和完整报告套件的新增数量为零；仅保留对话模式不伪称有磁盘恢复能力。
NFR-003：能力声明——工作流边界和检查点检测与全局强制写入拦截分开描述；只对实际验证的文件集合和时间范围给出结论。
NFR-004：数据保护——台账和报告不包含凭据、私有会话内容的外部副本或无关业务数据；原需求调研阶段的公开检索未向外部模型发送本地 Skill 内容；后续执行按另行确认的数据范围进行。
NFR-005：职责隔离——需求交付、评审结束、产品行为测试、实现发布各自有状态，不能相互替代。

## 验收条件

以下保留已确认的验收条件。当前完成状态和验证范围见本文RTM及公开证据摘要；条件本身不因文档整理而改变。

| ID | 场景和可观察结果 |
| --- | --- |
| AC-001 | 连续确认多个问题或说“继续”，阶段仍为评审中；只有明确整场结束且门槛满足时按已有授权回写；“只保留结论”产生零正文更新 |
| AC-002 | 七种路由适用统一边界；调用 domain-modeling 等能力时仅返回决定，CONTEXT.md、ADR 等正式资产不被立即写入 |
| AC-003 | 连续回答三题，权威台账保持一份，问题/回答/证据可恢复；新增正式文档版本和完整报告套件为零；明确不落盘时只有对话记录 |
| AC-004 | 尝试修改正文、版本、状态、时间、RTM 或生成逐题替代版本，工作流不执行；违规场景中的检查点变化被识别为违规，不能标为合格 |
| AC-005 | 阻塞或待修复返回不恢复编写；伪造 complete、未回答 P0 被遗漏于 openItems、无具体接受依据的 risk-accepted 均不能通过语义门槛 |
| AC-006 | 明确中途例外只影响指定对象和内容；台账可解析授权与前后基线；后续回答不继续写正文，超出范围时不执行 |
| AC-007 | 外部格式改动被保留且可在原范围内继续；语义冲突仅重开相关问题；新基线和未受影响决定仍可追踪 |
| AC-008 | 中断后恢复同一阶段与决定，无重复提问和自动回写；新证据触发重开时说明原因，保留被替代关系 |
| AC-009 | 首次集中回写内容与最终决定一致；同一决定集再次执行无重复内容和版本；模拟部分失败时结果为待修复，恢复不覆盖其他改动 |
| AC-010 | 参考适配规则明确排除 Spec Kit 逐题回写及被调用 Skill 立即写正式资产；检查所有关联文档无反向指令 |
| AC-011 | 一份字段正确但存在未授权文件变化的报告不能作为行为合格证据；验证明确列出检查对象、时间范围、结果和未验证能力 |
| AC-012 | 旧报告不被改写或补造确认；缺少结束或授权信息时不能自动回写；历史文件在迁移/恢复测试中保持原样 |
| AC-013 | 已确认且无新增证据的问题不重复询问；重开与新问题有缺口说明及原决定引用，不因固定问题数量制造无价值问题 |

## 当前RTM

| FR | AC | 当前状态 | 对应证据场景 |
| --- | --- | --- | --- |
| FR-001 | AC-001 | 已实现并在声明范围内验证 | test_default_batch_and_actual_postconditions；test_cli_open_p0_answer_and_exception_finish；原生Agent前向场景（见evidence-summary.json） |
| FR-002 | AC-002 | 已实现并在声明范围内验证 | seven route packs reviewed；领域建模双模式前向场景（见evidence-summary.json）；shared generic phase gate |
| FR-003 | AC-003 | 已实现并在声明范围内验证 | test_conversation_only_init_writes_no_ledger；test_cli_propose_question_and_prepare_plan_round_trip；原生Agent前向场景（见evidence-summary.json） |
| FR-004 | AC-004 | 已实现并在声明范围内验证 | test_paths_and_semver_versions；actual junction regression；TQA-006；TQA-012；TQA-013；TQA-017 |
| FR-005 | AC-005 | 已实现并在声明范围内验证 | test_unresolved_p0_and_concrete_risk_acceptance；test_forged_closure_and_checkpoint_evidence_are_refused；TQA-001；TQA-002 |
| FR-006 | AC-006 | 已实现并在声明范围内验证 | test_exception_is_bounded_and_single_use；test_cli_open_p0_answer_and_exception_finish；TQA-009；TQA-016 |
| FR-007 | AC-007 | 已实现并在声明范围内验证 | test_external_drift_and_new_version_block_batch；test_format_only_reconciliation_keeps_unrelated_decisions；TQA-003；TQA-008 |
| FR-008 | AC-008 | 已实现并在声明范围内验证 | test_pause_resume_reopen_preserves_history；TQA-011；TQA-015 |
| FR-009 | AC-009 | 已实现并在声明范围内验证 | test_partial_receipt_records_recovery；test_unchanged_postcondition_is_explicit_noop；TQA-004；TQA-007；TQA-010；绝对路径计划公开接口回归（见测试结果） |
| FR-010 | AC-010 | 已实现并在声明范围内验证 | baseline-selection and shared-contract adapters reviewed；four package validators；领域建模双模式前向场景（见evidence-summary.json） |
| FR-011 | AC-011 | 已实现并在声明范围内验证 | test_report_is_exact_ledger_projection；TQA-001；TQA-002；TQA-004；TQA-017；source manifests |
| FR-012 | AC-012 | 已实现并在声明范围内验证 | test_legacy_is_read_only_and_storage_cannot_overlap；14 legacy tests；TQA-005 |
| FR-013 | AC-013 | 已实现并在声明范围内验证 | test_pause_resume_reopen_preserves_history；test_cli_propose_question_and_prepare_plan_round_trip；native agent question/answer/closure turns |

“已验证”限定于[测试结果](test-plan-and-results-v1.0.md)所列方法、主机及前向场景。它不代表13个简单测试，也不代表对所有未来Agent行为的形式化证明。

## 非目标与能力边界

不提供OS/全局写入拦截，不自动判断外部变化是否具有需求语义，不安装依赖、不复制凭据、不重写历史确认。目录联接已实测；文件符号链接创建受测试主机权限限制，具体跳过见证据摘要。

## 来源与追踪

- [现行阶段契约](../../skills/grill-system/references/phase-boundary-contract.md)
- [公开证据摘要](evidence-summary.json)
- [文档复核记录](document-review-v1.0.md)
- [验收与发布](acceptance-release-v1.0.md)
