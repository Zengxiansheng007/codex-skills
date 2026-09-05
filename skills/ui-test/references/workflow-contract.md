# Workflow Contract

Read this reference when defining the end-to-end process, ownership, inputs, outputs, or stage exit criteria.

## Canonical Flow

```text
需求资料输入
→ Codex 需求理解与测试点拆解
→ Codex 执行前评审
→ 生成/修正 explore-steps
→ 安全策略检查
→ Midscene-first UI 探索
→ Playwright 确定性校验与 fallback
→ Solution D 证据采集与失败归因
→ Codex 执行质量评审
→ 问题分类：业务缺陷 / 测试资产问题 / 环境数据问题 / 需求不清
→ Codex 生成修复方案
→ 风险门禁：自动修复 / 人工确认 / 禁止执行
→ 修复上游 steps / 断言 / policy / evidence / fallback
→ 必要时重跑验证
→ 生成业务测试报告 + Agent 执行质量报告
→ Memory 分级沉淀
→ 满足条件后沉淀为 Playwright / Hybrid 回归脚本
```

正式业务run在报告前还必须完成以下不可倒序的close-out：

```text
最终pytest teardown TestReport
→ AttemptV2 finalization_started
→ RunResultV5/evidence候选
→ content-addressed objects
→ 单一原子commit manifest
→ 成功RunFinalizationReceipt
→ 唯一passed terminal
→ PytestSessionResultV1
→ 进程结束后外部PyCharmAcceptanceResultV1
```

任一失败只能进入failure receipt及failed/error/interrupted/unresolved路径；事后恢复不能补写passed或追认原helper进程通过。

## Roles

| Component | Responsibility | Must not do alone |
|---|---|---|
| Codex | Understand requirements, generate test points/plans, orchestrate execution, review quality, classify issues, propose and apply safe repairs | Declare business success without execution evidence |
| Midscene | First-pass visual understanding and semantic UI operation | Prove API, task, or downstream completion |
| Playwright | Deterministic verification, network capture, bounded fallback, stable regression | Hide Midscene failures or replace requirement reasoning |
| Solution D | UI/API/contract/task/downstream evidence, business IDs, timelines, failure attribution | Infer missing requirements |
| Memory | Store graded strategies, causes, fixes, constraints, and evidence references | Promote one-off or unverified behavior |
| pytest runtime plugin | Own ExecutionContextV3, AttemptV2, finalization ordering, terminal and SessionResult | Let a project adapter write terminal or self-declare acceptance |
| Finalization store | Persist content-addressed RunResultV5/evidence objects and atomically publish one commit manifest plus receipt | Treat staging, orphan objects or fixed legacy filenames as committed |
| External acceptance evaluator | Bind authorization, helper identity, process exit, SessionResult and finalization closure | Run UI, mutate canonical results or accept post-run recovery as passed |

## Required Inputs

- PRD, design, Figma export, HTML prototype, or scoped natural-language requirement
- environment URL and account role
- test scope and excluded scope
- known business states, API/downstream entry points, and test-data rules
- forbidden actions and approval boundaries
- model gateway/privacy authorization when private screenshots are involved

## Required Outputs

- test-point list and traceability mapping
- execution-ready exploration plan
- per-step screenshots and structured evidence
- business test report
- Agent execution quality report
- RunResultV5/evidence object closure, one commit manifest, receipt, terminal and PytestSessionResult for every new formal business node
- external PyCharmProcessEvidence plus file-read PyCharmAcceptanceResult for any claimed PyCharm or human R2 pass
- issue classification and repair plan
- Memory decision
- Playwright/Hybrid asset only when promotion gates pass

## Exit Criteria

A run is complete only when:

1. the target state is deterministically verified;
2. evidence is complete and redacted;
3. failures and degradation are classified;
4. repairs are re-verified or explicitly deferred;
5. reports link to all evidence;
6. Memory and regression promotion decisions are recorded;
7. pytest 阶段结果、业务 write state、人工 PyCharm 验收和整体完成状态互不替代（见 [execution-contracts.md](execution-contracts.md#execution-governance-separation)）；
8. 人工 A/B 真实 R2 均通过前，整体状态不得为 `passed` 或 `completed`。
9. 新正式business run使用2.2/ExecutionContextV3/AttemptV2/RunResultV5，且commit与成功receipt均早于唯一passed terminal；
10. PytestSessionResult与真实helper exit均为0、无post-run recovery，并由外部AcceptanceResult验证；旧2.1/V2/V1/V4只保留审计可读性。
