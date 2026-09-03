# UI-Test 逐模块断言修复开发计划 v1.0

状态：`implementation-running`

| Story | 交付 | 验证 |
|---|---|---|
| ST-01 | 扩展 Source/Test Data/IR/manifest Schema 与 PageModuleRegistry | 正反 Schema 测试 |
| ST-02 | Compiler v2 覆盖矩阵、postcondition 解析和五投影同源 | projection identity tests |
| ST-03 | 天津 A/B 恢复 F01～F12/A01 逐步语义 | A/B compile Golden |
| ST-04 | Page/Component 实际值读取、有效渠道默认、城市级联、版本预览 | adapter unit tests + pre-submit UI |
| ST-05 | recursive aggregate v2 与 strict manifest/verifier | aggregate Golden |
| ST-06 | inactive prepare + qualification-gated activation | transaction/rollback tests |
| ST-07 | 规范、Change Record、PRD/架构/测试/RTM 回填 | landed review |
| ST-08 | 全局安装、正式 successor、active 和公开 GitHub | hash/readback/remote SHA |

实施顺序固定为 workspace 测试、全局备份安装、formal dry-run、prepare、A/B qualification、activate、formal verify、GitHub publish。不得使用历史 A-011/B-001 代替新 build 的 qualification。
