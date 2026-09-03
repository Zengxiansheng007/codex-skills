# UI-Test 文档治理回顾调整记录

状态：`accepted / 已接受`  
规范 Envelope：`envelopes/change-record-v1.0.envelope.json`  
需求锚点：`RA-UI-TEST-REPAIR-20260830@v0.7`  
说明：旧版本保持只读；本文件是当前后继版本，不回写历史文档。


## 变更原因

旧的 2026-09-03 文档把产品 build 指纹复用于文档 source fingerprint、使用非规范嵌套 envelope、将 RTM 聚合为范围行，并在 CompletionEvaluator 之前宣称完成。实现与正式验证本身有效，但文档治理不能据此直接判为完成。

## 影响与分类

- 变更类型：文档治理与证据链修复；`semanticRequirementChange=false`。
- 需求影响：不新增、不删除 FR/AC；把实施期间已由用户确认的服务范围级联、浏览器兼容、认证入口 fallback、单次 R2 和清理边界并入完整 PRD。
- 架构影响：补充 as-built 组件与职责边界，不改变全局/项目分层决策。
- 计划与测试影响：保留原计划设计，新增逐 Task、逐 TCOV 实际状态与证据。
- 历史影响：旧文档和旧运行结果只读；通过 `supersedes` 与 current index 切换当前版本。

## 修复内容

1. 为 PRD、架构、开发计划、测试方案、RTM、Phase/Story、变更记录、Anchor 和 Completion Decision 生成规范 flat envelope。
2. PRD v0.5 成为完整独立基线，不再只写“继承范围”。
3. RTM v1.2 恢复逐需求行，并显式登记 EVD-001～EVD-018。
4. 文档 content hash、source set hash、候选差异评审、最终 no-drift 复核和 document manifest 均由固定脚本生成。
5. CompletionEvaluator 在独立结构/证据校验、Landed Review 和发布预检之后执行。

## 发布边界

GitHub 仅发布当前全局通用 `ui-test` 和本脱敏文档包；不发布项目适配器、正式项目目录、私有 URL、凭据、请求载荷或原始运行证据。
