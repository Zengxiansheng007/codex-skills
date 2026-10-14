> 公开投影：业务规则与原编号保留；“本轮”指源文档编写阶段。源哈希、路径适配与当前发布范围见 jmeter/docs/publication-context.md 及导出清单。

# JMeter 前置脚本 Skill：可复用工具与产品调研

查证日期：2026-10-13。当前只做公开资料研究与需求澄清；未安装工具、未运行 JMeter、未调用远程转换服务、未接收或外发 Cookie/账号。技术结论来自各项目官方文档或作者源码仓库；作者声明与独立实测分开记录。

## 结论

**已有成熟的底层工具，也找到同类 Agent 产品和 Skill；尚未找到经本轮验证可直接覆盖本需求全部闭环的现成方案。** 当前最薄的组合候选是：本地确定性 cURL 解析及原生 JMX 生成 + JMeter 原生组件 + 低负载试跑与证据核验 + 面向既有 `jmeter-tps-runner` 的交接约束。这里是研究建议，尚未选定实现与开发授权。

1. **优先核验 Apache JMeter 自带 cURL 解析能力。** 它不是只能手工录制；官方已有 cURL 导入。5.6.3 的公开解析类可以作为本地解析候选，但 GUI 导入动作并非现成无头转换 CLI，仍需最薄适配。[官方 cURL 手册](https://jmeter.apache.org/usermanual/curl.html)、[BasicCurlParser API](https://jmeter.apache.org/api/org/apache/jmeter/protocol/http/curl/BasicCurlParser.html)、[5.6.3 导入动作源码](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/protocol/http/src/main/java/org/apache/jmeter/protocol/http/gui/action/ParseCurlCommandAction.java)
2. **QAInsights 的 cURL/HAR→JMX 工具是功能最接近的开源转换候选。** 其网页工具及 MCP 已公开；本轮只确认作者文档与仓库，未完成转换实现及测试源码审计，不能用“production-grade”宣传语代替本地兼容验收。[转换器](https://docs.jmeter.ai/tools/curl-to-jmx/)、[作者仓库](https://github.com/QAInsights/docs.jmeter.ai)
3. **Feather Wand 是最接近“AI 编写、检查与执行 JMeter”的同类产品。** 适合借鉴读树—修改—回读校验、关联探测、保存计划的机制；把完整 GUI 插件搬入 WorkBuddy 会增加依赖，当前不作为默认实现。[作者仓库](https://github.com/QAInsights/jmeter-ai)
4. **MeterSphere 必须按版本拆开。** v3 有 cURL 导入，但官方明确 v3 不再提供性能测试；v2 的 JMX 导出与性能测试不能拼接成 v3 当前能力。[v3 cURL 导入](https://metersphere.io/docs/v3.x/user_manual/api_test/debug/)、[版本更新日志](https://metersphere.io/docs/v3.x/about/changelog/)

## 工具/产品对照

| 候选 | 已查证的方案 | 本次适配与限制 | 复用判断 |
|---|---|---|---|
| Apache JMeter 原生 cURL 导入 | GUI 中导入单条、多条或文件中的 cURL，生成 HTTP 请求；公开 `BasicCurlParser.parse()` 返回请求模型。[手册](https://jmeter.apache.org/usermanual/curl.html)、[API](https://jmeter.apache.org/api/org/apache/jmeter/protocol/http/curl/BasicCurlParser.html) | 请求转换不等于业务断言、会话策略与 runner 兼容验收；官方手册未提供 `jmeter --import-curl` 无头入口。 | 原生解析/组件第一候选；先做解析语义与无头输出 PoC。 |
| JMeter HTTP(S) Test Script Recorder | 浏览器经 JMeter HTTP(S) 代理，录制请求为测试计划；HTTPS 涉及证书。[组件手册](https://jmeter.apache.org/usermanual/component_reference.html#HTTP(S)_Test_Script_Recorder) | 适合完整浏览器业务流；对于工程师已经复制 cURL 的场景，重新录制不是最薄路径。 | 保留为复杂链路补充输入方式，首期不必引入。 |
| QAInsights cURL/HAR→JMX + MCP | 文档提供请求转换、主机/Token 参数化、状态码断言、Cookie Manager、时长等选项；浏览器端本地转换，托管 MCP 收到输入。[转换器文档](https://docs.jmeter.ai/tools/curl-to-jmx/) | 默认 200/201/204 断言不是业务契约；托管 MCP 需要数据外发边界。公开仓库 Apache-2.0，但转换核心及测试覆盖尚未逐文件核验。 | 候选本地复用，暂不发送真实 cURL 给远程 MCP。 |
| MeterSphere v3 | 从浏览器/Charles/Fiddler cURL 导入，认证可用 Cookie、前置脚本 Token 等。[接口调试](https://metersphere.io/docs/v3.x/user_manual/api_test/debug/) | v3 不提供性能测试；本轮没有查证 v3 本地 JMX 导出的完整路径。 | 参考接口准备交互，不作为现成性能测试流水线。 |
| MeterSphere v2 | 文档记载接口/场景可导出 JMX；性能模块可加载 JMX、参数文件，运行并下载 JTL/执行资源。[FAQ](https://metersphere.io/docs/v2.x/faq/api_test/)、[报告](https://metersphere.io/docs/v2.x/user_manual/load_test/test_report/) | 官方版本说明称 v2.10 社区版停止维护；重平台部署不符合本地轻量 Skill 的最低成本。 | 历史方案参考，不能推荐为了本需求新部署旧版。 |
| Taurus | 用 YAML/JSON 描述请求，生成 JMX；支持请求头、数据源、断言、提取器；也可执行已有 JMX。[官方 JMeter 执行器文档](https://gettaurus.org/docs/JMeter/) | 本轮未查到该文档中的直接 cURL 导入入口；需另建 cURL→Taurus 请求模型，还引入执行框架与默认行为。 | 团队已有 Taurus 时可适配；当前不是最薄新增依赖。 |
| BlazeMeter / Proxy2JMX | 云端可接收 JMX；Proxy2JMX 将 Selenium 运行流量转成 JMX，仅转换请求，不包含断言/其他逻辑，需 BlazeMeter API key。[官方 API](https://help.blazemeter.com/apidocs/performance/tests_create_a_test.htm)、[作者 Proxy2JMX 文档](https://github.com/Blazemeter/taurus/blob/master/site/dat/docs/Proxy2JMX.md) | 不应把文档里的 cURL 调用 BlazeMeter API 错认为“用户业务 cURL 转 JMX”；云端/代理方式有额外账户与流量边界。 | 完整平台参考，首期本地路径不需要。 |
| jmeter-java-dsl | 以 Java API 构建/执行测试计划，可 `saveAsJmx()` 导出，也可读取 JMX；Java lambda 导出可能需要改写及额外 jar。[官方指南](https://abstracta.github.io/jmeter-java-dsl/guide/#jmx-support) | 本轮指南未发现已文档化的直接 cURL 导入接口；Java 工程和依赖对同事部署增加成本，需约束只生成原生元素。 | 已有 Java/Maven 工程时优选；否则作为生成器备选。 |
| Feather Wand / jmeter-ai | JMeter 内的 Agent 读取树、添加元素、修改属性、回读配置；可保存计划、探测关联、应用提取器。[作者 README](https://github.com/QAInsights/jmeter-ai) | 是 JMeter GUI 插件，需模型/CLI 配置；并非现成 WorkBuddy 前置 Skill。未独立测试 cURL 和 Cookie.csv 工作流。 | 借鉴机制；不因为功能相似直接迁移插件。 |

以上“复用判断”均为结合用户场景的推断，不是项目作者的承诺。

## 原生解析路径为什么可复用，以及哪里仍需适配

在固定 5.6.3 标签中，`BasicCurlParser` 使用命令分词和选项解析构建请求对象；选项有支持、忽略、不支持及需 JMeter properties 配置的分类。它不是 Bash 解释器。`ParseCurlCommandAction` 内部把请求模型映射为 sampler、header、cookie/auth 等元素，其中 sampler 构造方法为私有且依赖 GUI 工作流。[解析源码](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/protocol/http/src/main/java/org/apache/jmeter/protocol/http/curl/BasicCurlParser.java)、[导入动作源码](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/protocol/http/src/main/java/org/apache/jmeter/protocol/http/gui/action/ParseCurlCommandAction.java)

**设计推断：** 可先验证“直接调用现有解析器 → 统一请求模型 → 固定模板/原生 API 序列化 JMX”，避免重新实现所有 cURL 选项；不得声称“已有官方无头 converter，直接调用即可”。生成结果仍需按用户选定的脚本规范核验。输入作为数据解析，不 `eval`、不运行收到的 Bash。尤其应对 Bash `$'…'`、换行续行、URL 编码、重复参数、文件引用、Cookie、多请求等做语义样例验收。

## 现成 Agent Skill：找到什么，缺什么

| Skill 项目 | 作者公开范围 | 能否完整替代本次 Skill |
|---|---|---|
| Abstracta `jmeter-dsl-skills` | `jmeterdsl-basic-script` 生成 Java/JUnit 性能脚本；`jmeterdsl-official-doc` 查询官方文档；Apache-2.0。[仓库](https://github.com/abstracta/jmeter-dsl-skills) | 不完整：不是工程师 cURL→原生 JMX→Cookie 策略→runner 准入的完整流程。可复用提示结构，但不能照搬其示例阈值。 |
| QAInsights `perf-skills` | 性能测试知识型 Skill，覆盖 JMeter、多工具、关联、断言、脚本生成与诊断；MIT。[仓库](https://github.com/QAInsights/perf-skills) | 不完整：指导型知识库不等于固定转换器与真实试跑验收器。适合只取相关参考条目并回查原始来源。 |
| MeterSphere `metersphere-skills` | 面向 OpenClaw，封装资产查询、功能用例生成、OpenAPI 接口定义/用例生成及系统写入。[官方组织仓库](https://github.com/metersphere/metersphere-skills) | 不匹配：当前公开范围没有本地 cURL→JMX 和 JMeter 试跑交接；仓库首页未显示许可证，复用代码前还需确认。 |

只可表述“本轮已找到这些相近 Skill”；不能据有限检索证明全球不存在完全同类方案。

## 成熟度与许可证证据

| 项目 | 当前可查证证据 | 本轮不声称的内容 |
|---|---|---|
| Apache JMeter | 官方当前下载为 5.6.3；Apache 官方项目，仓库 Apache-2.0。[下载](https://jmeter.apache.org/download_jmeter.cgi)、[仓库](https://github.com/apache/jmeter) | 不把 master 的 Java 要求当作 5.6.3 运行要求；不声称所有 Bash cURL 语法保真。 |
| jmeter-java-dsl | 官方发布页最新 2.3，资产时间 2026-10-07；多版本历史可见。[发布](https://github.com/abstracta/jmeter-java-dsl/releases) | 版本活跃不等于本需求的脱离 DSL/JAR 的导出兼容已验收。 |
| Taurus | 官方作者仓库 Apache-2.0；发布页列 1.16.51 与多版本历史。[许可证](https://github.com/Blazemeter/taurus/blob/master/LICENSE)、[发布](https://github.com/Blazemeter/taurus/releases) | 未在本环境安装或运行。 |
| Feather Wand | 作者仓库 MIT；发布页 v3.8.8，2026-10-12。[仓库](https://github.com/QAInsights/jmeter-ai)、[发布](https://github.com/QAInsights/jmeter-ai/releases) | 活跃社区产品，不据 README 推定企业级可靠性。 |
| QAInsights converter | 作者仓库 Apache-2.0，公开 tests 目录；本轮具体转换源码路径通过浏览器工具读取失败。[仓库](https://github.com/QAInsights/docs.jmeter.ai) | 未核实单个模块许可证/依赖/全测试覆盖；未运行远程 MCP。 |
| MeterSphere | v3.6.9 官方日志，v2 社区版停止维护；现行 v3 LICENSE 为 GPLv3 加附加条件，日志称 FIT2CLOUD Open Source License。[日志](https://metersphere.io/docs/v3.x/about/changelog/)、[当前许可证](https://github.com/metersphere/metersphere/blob/v3.x/LICENSE) | 不把旧 GPLv3 或旧性能模块当作当前 v3 产品及许可事实。 |

许可证内容是来源核对，不构成法律意见；本轮未复制第三方源码、未将其纳入分发包。

## 首期复用路线建议（待需求确认）

建议首先比较两条本地生成 PoC：

- **A：复用 JMeter 5.6.3 BasicCurlParser + 原生元素映射。** 依赖与执行环境接近既有 runner。缺口是无头映射、Bash 语法保真及规范化报告。
- **B：审核 QAInsights converter 的本地代码后最薄适配。** 功能覆盖更接近，但须先取得精确模块/许可证/测试证据，并锁定源码版本；远程 MCP 不是处理真实 Cookie 的默认路径。

现有 runner 应继续负责已确认计划下的寻峰；新增 Skill 负责脚本准备、认证方案确认、断言方案确认、低负载试跑及准入证据。该职责分割是场景推断，待 grill 确认，不能在未读取 runner 真实契约前假定任意 JMX 都兼容。

## 待澄清与验收建议

1. **Cookie.csv 是哪一种格式？** Cookie 请求头字符串表、每用户多列数据，还是 cookie jar？这些不是同一格式。当前工具资料没有覆盖用户要求的“登录后存 cookie.csv 再供寻峰”的完整互操作契约，不能自动混用。
2. **登录频次与账号模型。** 一次预取、多账号预取、每线程登录、每轮刷新会影响被测业务与错误率；单条复制 cURL 不能证明应选哪种。
3. **断言的业务依据。** 状态码仅能证明部分协议行为；需工程师提供或确认业务成功标志、响应字段与允许值。转换器默认状态集合不应代替业务事实。
4. **默认请求头。** 应核验捕获请求与删除/继承规则；不能给所有请求强加相同 `Content-Type` 或把浏览器临时 Cookie 写死。
5. **试跑范围。** 明确脚本可加载、请求成功、认证成功、断言有效、文件依赖可解析、官方报告可生成、runner 可识别目标/前置等判据；“程序退出 0”不能单独作为通过。
6. **验证样例。** PoC 只需覆盖拟支持的 cURL 选项与本地模拟登录/认证/失败响应；已有 JMX 除静态检查外，需要独立授权的有限试跑。生产/真实业务发压另行确认具体目标与预算。

以上为研究导出的需求问题与建议，未固定默认并发、时长、Cookie 格式或成功阈值。
