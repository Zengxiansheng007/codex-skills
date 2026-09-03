# UI-Test 逐模块断言修复测试方案 v1.0

状态：`passed / xmind-desktop-external`

## 自动化层

- Schema/Compiler：必填字段、覆盖缺口、默认期望、未知模块、复合步骤、断言 ID 唯一性。
- Projection：Human/Midscene/Resolved/manifest/Playwright 的步骤与断言一致。
- Component：标题、普通/富文本、来源、类型、城市、渠道、受众、日期、版本逐步读回。
- Aggregate：历史层级 Golden、公共前置一次、A/B 各一次、参数原子节点、禁止 `<br>` 和拼接。
- Sync/Deploy：prepare 不改 active；qualification 集合不完整拒绝；CAS 冲突回滚。

## 正式提交前验证

A/B 各使用一个新 qualification Run ID，执行 S00、S01 和除 F12 外全部 feature 步骤。结果必须通过 Schema、步骤全集、截图哈希及零写约束。浏览器网络或控件不稳定视为 qualification 失败，不降低断言。

## 回归与发布

- workspace 全量 pytest；安装后全量 pytest。
- 新旧 active、历史 runs/reports/releases/JSONL 哈希边界对比。
- formal verifier 重算 aggregate 与结构约束。
- GitHub 作用域、敏感扫描、提交 SHA、本地/远端文件内容一致。

## 退出标准

专项仅在全部自动化、两份 qualification、active 事务、formal verify 和 GitHub 校验通过后标记完成。整体治理仍保留已明确排除的 repair-needed 项。
