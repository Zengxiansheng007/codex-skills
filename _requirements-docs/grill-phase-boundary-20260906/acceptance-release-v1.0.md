---
artifact:
  id: ART-GRILL-RELEASE-PUBLIC-001
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
# 验收、安装与发布 v1.0

**代码实现、全局安装及GitHub发布已完成。** 代码发布基线为[b4fa506](https://github.com/Zengxiansheng007/codex-skills/commit/b4fa50611f2f4c627903df2cc439ff483ce6cfc6)，四个入口文件曾按该不可变提交从GitHub回读，HTTP200且与提交blob一致。

## 版本与文件数

- 原验收候选包含69个非缓存源文件，新增26、修改27、删除0；该阶段快照保持原状。
- 公开代码发布包含71个非缓存文件：增加了可移植发布文档及其记录，排除了未封存的编译缓存。
- CR-20260906-006将write-prd中的本机路径改成安装位置可解析的说明。运行时Python、Schema和测试行为未因这项适配改变。
- 本轮新增公开项目文档，并修正少量Skill说明/历史状态标注；这些文档文件数不应倒算成代码发布时的71个文件。

安装后8项检查通过。安装使用逐目录原子替换与受控回滚，保留完整备份和原目录；不是四目录的单一原子事务。备份位置、审批原件和包含本机路径的操作回执只保存在本地。

## 发布范围

| Skill | 代码入口 |
| --- | --- |
| grill-system | [SKILL.md](../../skills/grill-system/SKILL.md) |
| write-prd | [SKILL.md](../../skills/write-prd/SKILL.md) |
| write-requirements-prd | [SKILL.md](../../skills/write-requirements-prd/SKILL.md) |
| domain-modeling | [SKILL.md](../../skills/domain-modeling/SKILL.md) |

GitHub目标为Zengxiansheng007/codex-skills的main。此前发布核对了远端SHA、71个提交文件内容和四个公开入口。Git按原有换行设置进行规范化；不要将安装文件原始字节哈希与Git规范化blob哈希混为一谈。

此次未进行GitBook同步。全局development-system、模型配置、网络或凭据配置未因本次任务被修改。

## 变更记录

CR-20260906-001—005记录阶段隔离实现及关联修复，CR-006记录发布可移植适配。CR-007—010记录本轮公开文档、接口说明及分类台账状态澄清。

[Grill记录索引](../../skills/grill-system/change-records/index.md) · [PRD路由索引](../../skills/write-prd/change-records/index.md) · [需求编写索引](../../skills/write-requirements-prd/change-records/index.md) · [领域建模索引](../../skills/domain-modeling/change-records/index.md)

完成评估验证了实现、证据、独立QA、范围与权限门槛。本次公开[证据摘要](evidence-summary.json)保留结论及来源哈希，未公开原始任务/模型/审计日志。

