# UI-Test 总测试用例与逐模块断言修复需求 v1.0

状态：`approved / implemented`
需求锚点：`RA-UI-TEST-MODULE-ASSERTION-20260903@v1.0`

## 目标

恢复天津公告创建 A/B 的逐页面模块语义，使 Source Case、Human、Midscene、Resolved、参数清单、Playwright 和产品总测试用例由同一编译模型生成；修复产品聚合层级被 Human View 拼接破坏的问题。

## 范围

- A/B 覆盖公告类型、标题、内容、来源、管理权力归属、服务范围、有效渠道、个人/法人、有效期；B 另覆盖弹窗版本号，A 将该模块标记为不适用。
- 未填写的有效渠道必须独立断言默认精确无序集合：`APP端`、`PC端`、`支付宝小程序端`、`微信小程序端`。
- 每个适用模块必须有独立步骤和即时读回 postcondition；禁止一个页面步骤合并多个模块。
- 产品总用例固定保留 `项目组 -> 产品 -> 系统 -> 模块路径 -> 功能 -> 公共前置/用例 -> 操作/断言`。
- 公共 VPN、登录和进入创建页只展示一次；每个操作恰有一个参数节点和一个预期节点。

## 功能需求

| ID | 需求 |
|---|---|
| FR-01 | Source Case v2 每步强制 `module_id` 和至少一个含稳定 ID、operator、expected_ref、evidence 的 postcondition。 |
| FR-02 | 项目提供 PageModuleRegistry，并为每个分支声明 `operate/assert-default/not-applicable`。 |
| FR-03 | Test Data 是业务值及默认期望的唯一可编辑来源。 |
| FR-04 | 编译前生成模块覆盖矩阵；缺失、未登记、默认期望缺失或复合页面步骤时停止所有投影。 |
| FR-05 | Human、Midscene、Resolved、参数清单和 Playwright 共享步骤、模块、期望与断言身份。 |
| FR-06 | Playwright 在每次操作后读取实际值；有效渠道只读断言；服务范围验证上级天津市及和平区可见后代级联。 |
| FR-07 | v2 产品聚合器递归生成 Outline、Markdown 和严格 manifest，禁止 Human View 拼接及 `<br>`。 |
| FR-08 | 正式 verifier 重算并校验结构、内容、哈希、included cases 和 Golden 约束。 |
| FR-09 | 正式发布采用 inactive prepare、A/B no-submit qualification、CAS activation 三阶段。 |
| FR-10 | qualification 必须为 `submit_count=0`、`write_state=not_attempted`、`sequence_allocated=false` 并绑定截图哈希。 |

## 验收标准

- AC-01：缺 `module_id/postconditions`、默认期望、注册项或包含多个页面模块时分别返回稳定错误码。
- AC-02：A/B 所有适用模块恰有一个覆盖项；A 版本号不适用，B 版本号为操作项。
- AC-03：五种投影的 step/module/assertion/expected 集合一致。
- AC-04：总用例只有一个公共前置，两个用例标题各一次，产品与系统同名仍保留两层。
- AC-05：旧 release、RunResult、报告和 JSONL 哈希不变；successor 在激活前保持 inactive。
- AC-06：A/B qualification 均通过且无提交、无业务请求、B 无序列分配后才允许 active 切换。
- AC-07：全局 Skill、项目适配器、作用域扫描、敏感扫描和 GitHub 远端校验通过。

## 边界

不执行 R2 提交，不创建或删除公告，不修改历史结果，不写 D:\RAG，不同步 GitBook。diagnostics、孤儿 Run、Runtime 分类和 Completion 自证缺陷继续作为独立 `repair-needed`。
