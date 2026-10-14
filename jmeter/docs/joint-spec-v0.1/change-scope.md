> 公开投影：业务规则与原编号保留；“本轮”指源文档编写阶段。源哈希、路径适配与当前发布范围见 jmeter/docs/publication-context.md 及导出清单。

# 源基线、准确改动范围与差异处理 v0.1

日期：2026-10-14。本页记录未来开发位置，不是已经执行的修改清单。主规格中不以具体路径作为接口；进入实现前重新核对本页和 [source-baselines.json](source-baselines.json)，保留用户已有改动。

## 1. 源选择与历史保留

runner 候选 A：`work/jmeter-workbuddy-development-20260921/candidate/jmeter-tps-runner`。

runner 打包源码 B：`work/jmeter-workbuddy-development-20260921/packaging-20260921-192019/source/jmeter-tps-runner`，MANIFEST 仍标 0.3.0 / candidate-pending-host-validation；目录存在不是已安装、正式发行或当前同事环境证明。

拟在新的隔离候选中以 **B 为起点、A 为历史对照**。本轮只核对源，不复制/改写它们，不覆盖已安装 Skill。两套 scripts 顶层相同文件名逐项 SHA 对照，实际有四处差异：

| 文件 | A SHA256 | B SHA256 | 必须保留的 B 能力 |
|---|---|---|---|
| scripts/controller.py | BADC38AE66DDFDDE39FC3913A17824F1BB0F67DB50ACB7517F5C8262E305BB54 | 524F675AECDF7AD023C6AB0ED9E715B98755F1BFB088E09E2E68CABBF0340A62 | 结构化汇总交接 Word 产物 |
| scripts/report.py | EC79C9B9539ADE0A6B20BD1ACFE0B472FE9467F048BDEED311FBE7E7B97E6293 | A8411DC4F13893AB7B7E318607540CD265B86920E9A22C3EC473BDC7249BBE67 | 官方 errorsTable 的非评分错误附录字段 |
| scripts/summary.py | 351D29838646DA90BD8B48F1B3268CA1A0B483E7F4AE7D6C5D6DDD9303DCCBF8 | 497099927AD81B6DA3C61E76CCD268E5DB806538F109D8AC59E69C92C0618543 | Word、展示取舍/24小时制、错误明细附录；JSON原值保留 |
| scripts/workbuddy_bridge.py | 7B0AA883C0CF47FB77B445E0A1DEAE357FA98DE942B6B267AC289C844A6E42CF | 322F84D4DCA15F838BB438B09CD3F8FA023047C8CB9984C598114F433264F37C | summary.docx 的读取/完整性/交付核验 |

其余对应 scripts 文件本轮 hash 相同；这只证明两套当时字节相同，不证明全部代码资格或 B 已正式验收。未来若刷新发现其他差异，应先记录实际来源，不静默选较旧文件覆盖。

writer 尚无产品候选；`work/jmeter-preparation-skill-20261013` 里的需求、原型、规格是材料，不是已实现 Skill。拟新增独立候选包，与 runner 同属一个新开发根。

## 2. writer 新增写集

文件名是未来模块建议，实施前绑定准确开发目录；本轮没有创建这些产品文件。

| 拟模块/资源 | 责任 | 需求 / 计划 |
|---|---|---|
| SKILL.md、references/使用与输入说明 | 条件补问、固定入口、默认断言、失败停止、交接与实际版本 | REQ-001–006；JP-03/04/08 |
| task_contracts / writer_entry | WriterTask/ValidationResult、固定 analyse/build/probe-auth/validate | REQ-001–006；JP-01/04 |
| curl_adapter 与本地 Java helper | 5.6.3原生解析的薄适配、原生 JMX 保存、保真/不支持诊断 | REQ-001；G-01，JP-01/03 |
| plan_builder | 请求/组级动态头、原生默认断言、CSV/认证结构、角色映射 | REQ-001/002/003/005；JP-03/05 |
| trial_copy | 1/0/1、单账号 CSV 引用及认证迭代隔离、独立副本比较 | REQ-004；JP-04/05 |
| execution / validation | 单次官方试跑、实际覆盖/退出/JTL、分层结果、无重试 | REQ-003/004/006；JP-04 |
| auth-contract schema、固定认证模板/信任说明 | JSON→CSV发布、绑定/本轮证据；新脚本生成职责 | REQ-003/007；JP-01/05 |
| CSV模板、入口行为夹具与测试 | 手填、账号格式及有效头/断言/单会话证据 | AC-001–007；JP-03–07 |

不复制 runner search/controller/监控服务到 writer。短验证执行参考既有安全 .bat 参数边界，但不抽取两个包必须同时安装的公共运行库。若 helper 需要构建，使用已有明确工具并记录构建/分发资格，不自动下载 JDK 或第三方依赖。

## 3. runner 必要写集

下表路径均相对于未来隔离候选，B 为拟起点。

| 文件/模块 | 必要改变及原因 | 归属 / 直接验证 |
|---|---|---|
| scripts/jmx.py | 明确认证角色/精确 HTTP 集；保留标准业务组及普通前置语义，正式副本仍仅并发/HTTP enabled | REQ-007；JP-05；R-03–05、原 jmx 回归 |
| scripts/preflight.py | 统一受控 setUp/模板/生成依赖资格；将新布局及无发压接收纳入同一路径 | REQ-007；JP-04/05；G-02/03、R-01–07/11 |
| scripts/authentication.py（新增） | AuthContract、受信模板、限定依赖与 AuthenticationResult 的唯一解释器；writer/bridge/controller 不各造一套判断 | REQ-003/007；JP-01/05；R-06–11、J-02/03/05/07 |
| scripts/root_config.py（新增） | 首次确认根的外置用户配置、只读/显式写入、无自动 fallback | WB-FR-009；JP-02；OR-01/04 |
| scripts/prepare_output.py（新增固定前置脚本） | prepare-task / prepare-round；独占预约、标准目录、准备证据、路径/链接边界 | WB-FR-010/011；JP-02；OR-02–05 |
| scripts/storage.py | 原任务/轮次存储接收合法预约；paths 不再绕过强制脚本自行创建；阶段记录与单写事件边界 | WB-FR-010/011/015；JP-02；OR-02–08，storage 回归 |
| scripts/process.py | 采样/报告分开官方调用，保存分别日志/退出；同一阶段执行适配器与精确报告控制接口 | WB-FR-012/013/015/020/021；JP-02/06；OR-06–08/15–17、J-09/11/12 |
| scripts/windows_report_process.py（拟新增，G-04后冻结） | 限定报告 Job/持有句柄、进程归属/退出观察；不扩散到任意 Java 或 writer | WB-FR-015/020/021/022；JP-06；G-04、J-11/12 |
| scripts/controller.py | 强制准备→采样→认证核验/独立report→评分；控制等待循环；报告技术问题/停止/退出未知；原 search 不变 | REQ-007，WB-FR-011–015/020–025；JP-02/05/06；R-08–12、OR-05–11/15–18 |
| scripts/report_monitor.py（新增） | 任务级观察、原报告600秒一次提醒、自退摘要、排他代次；不诊断/终止报告 | WB-FR-016/017/018/022；JP-06；OR-12–14/16、H-06/07/09/10 |
| scripts/report_control.py（新增） | 关联/幂等控制请求与结果、主owner处理、原报告退出复查 | WB-FR-020–022；JP-06；OR-15–17、J-11/12、H-08/09 |
| scripts/workbuddy_bridge.py | 统一接收；合法预约已存在不误拒绝；保留主监督；监控独立绑定/状态；阶段/认证/Word真实结果核验 | REQ-006/007，WB-FR-004–008/015–024；JP-02/04–06；entry/bridge回归、H系列 |
| scripts/runner.py | 新只读 check-input/能力投影、根/准备/阶段入口及旧参数的显式规范化 | REQ-006/007，WB-FR-009–013；JP-02/04；R-02/11、入口行为 |
| scripts/summary.py | 保留 Word/错误附录，增加实际并发/轮次、采样/报告状态、未完成搜索、保留峰值 | WB-FR-024；JP-02/06；OR-18、report/summary/bridge相关回归 |
| references、SKILL.md、MANIFEST.json、契约/模板/说明/相关tests | 回顾最终实现，拆分命令、根、监控/续建/停止/认证说明；清单敏感扫描 | 两包全部关联；JP-08；完整性与真宿主资格分开 |

**拟保持**：scripts/search.py 及 scripts/contracts.py 的寻峰模型/算法/预算/单位；scripts/report.py 的指标/P90/官方时间及 B 的错误附录解析；scripts/audit.py 的仅审计语义；scripts/host.py 的原答复不倒退规则；package_integrity.py 的根 _user_meta.json 唯一额外普通文件例外。若新结果结构迫使这些模块做必要小改，先登记直接原因/新增测试，不据“联合计划”扩成全仓重构。

## 4. 对旧规格的逐项处理

| 旧约束/接口 | 联合处理结果 | 依据与验证 |
|---|---|---|
| writer 原规格“保留 runner process/storage/原宿主机制” | 仅这部分建议被新 runner 增量覆盖；保持 writer 不承担正式运行 | WB-FR-009–025 已确认；本页 runner 写集、OR/H增量 |
| writer 原 runner 认证核验→读report | 精化为采样真结束→认证记录与同轮独立report→均适用通过后评分；认证失败不绕过完整JTL的report步骤 | REQ-003/007 + WB-FR-012–015/023；R-09、OR-10、J-08/10 |
| 原 Store.paths 内部创建，bridge output 必须不存在 | 新固定脚本预约；主入口排他认领已准备目录，任何未准备路径拒绝 | WB-FR-010/011；OR-02–05 |
| 原 Execution 单次合并退出 | sampling_execution/report_execution 独立；旧 execution 不冒充新双阶段证明 | WB-FR-012–015；OR-06–08、bridge相关回归 |
| WB-FR-003 默认12核心字节不变 | 只对本次必要模块解除“默认字节不变”建议；原算法/评分/JMX限制保持 | 增量 §8；本页精确写集，R-12、OR-09/18 |
| WB-FR-008 原先不新增杀树/恢复/重跑 | 新增仅用户决定的原报告停止/退出核查；unknown 原则继续；整主任务恢复/重放仍排除 | WB-FR-020–022；OR-15–17、G-04 |
| 只有主 bind-task，ack仅记答复 | 主绑定保留，监控按代次另绑；ack仍不控进程，新增 control-report | WB-FR-016–022；OR-12–17、H-06–10 |
| writer 短验证专门超时/进程树收尾排除 | **继续排除**；新 Windows 报告控制只属于 runner，不复用为 writer 新强停功能 | DC-021/Q20；W-15、scope检查 |
| 旧正式副本只并发+HTTP enabled；writer可改更多试跑字段 | **两份契约继续分开**；setUp/CSV生成结构必须在此限制内资格化 | REQ-004/007，WB-FR-025；W-12、R-04/05、J-07 |
| candidate Markdown 汇总与 B 的 Word/错误附录差异 | B 的 Word/精度/时间展示/附录继续；不回退 Markdown-only | 原打包源码事实；OR-18、J-08、H-04 |
| 旧 writer / runner 需求整份确认状态不同 | 保留原状态；本联合规格待审阅，不把新规格编写当追认需求/实机验收 | README与baseline，最终文档核对 |

历史文档原件全部保留。联合规格只作为本次协调版本，不能追溯修改旧测试或把旧未测项变成 passed。

## 5. 当前实际写集与未执行动作

本轮实际写入仅为 `work/jmeter-writer-runner-joint-20261014/` 的联合文档、来源哈希、研究证据和文档检查工具/结果；另由既有 PowerShell 治理器记录其自身错误与修正。没有修改旧需求/规格/原型、candidate、packaging、已安装 Skill、实际根配置或 JMX。

没有执行任何产品测试、登录、JMeter、Win32停止/诊断或WorkBuddy操作；没有调用Claude、创建开发票、变更流程状态、安装依赖或推送GitHub。
