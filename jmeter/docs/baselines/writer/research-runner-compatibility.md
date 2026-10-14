> 公开投影：业务规则与原编号保留；“本轮”指源文档编写阶段。源哈希、路径适配与当前发布范围见 jmeter/docs/publication-context.md 及导出清单。

# 前置 JMeter Skill 与现有 TPS Runner 的消费者兼容性核对

核对日期：2026-10-13。范围为指定源码和需求的只读检查；未读取用户 JMX、真实运行报告、账号或 Cookie，未执行 Python/JMeter，未修改既有 Skill、源码或 JMX。本文是接口研究，不是对历史运行或发行资格的重新验收。

## 本地来源与状态

指定全局位置 `<LOCAL_PATH>` 下的 `SKILL.md`、`references/supported-inputs.md`、`scripts/jmx.py`、`scripts/preflight.py`、`scripts/report.py` 均不存在（本次逐项 Test-Path 实测）。已按交接允许的后备位置读取工作区候选：

`<LOCAL_PATH>`

以下候选简称为 `candidate/`，并非当前全局已安装版本。

同时读取 `<LOCAL_PATH>`。该文件 frontmatter 仍为 `need-review`（12–13行），41行仅记录 Windows / WorkBuddy 5.5.6 / Git Bash / JMeter 5.6.3 环境。本文不据此继承任何历史运行授权或证明其他机器兼容。

## 最重要的结论

1. **通过 curl 生成“普通 HTTP + 标准 ThreadGroup + 内置配置/断言/提取器”的 JMX，存在直接兼容路径。**但 curl 本身不包含业务成功规则、凭据生命周期和前置依赖；必须把这些待确认项与结构兼容分开。
2. **“登录放 setUpThreadGroup，再在 JMX 内写 cookie.csv”不是当前 Runner 已支持的方案。**setUpThreadGroup 不在安全节点清单；常见写 CSV 所需的活动 JSR223 也不在清单。用户确认不能把 unsupported 变为通过。
3. **手工维护 cookie.csv 可采用现有 CSVDataSet，但路径必须解决副本迁移问题。**当前 Runner 会将运行副本放到输出目录；相对 cookie.csv 会触发布局阻塞，不能由 Runner 顺手改路径。
4. **仅“官方 JMeter 能跑”不等于“可交给 TPS Runner”。**新增 Skill 应分别交付单次试跑结果、当前 Runner 的静态兼容结果，以及尚未确认的认证/业务依赖。

## 消费者契约与证据

| 关注项 | 本地证据 | 对新增 Skill 的意义 |
|---|---|---|
| 原件与可修改项 | `candidate/SKILL.md:27–28`；`scripts/jmx.py:158–189,192–227`；`requirements-v0.3.1.md:22` | Runner 只改运行副本的目标标准线程组并发与所有 HTTP 的 enabled；新 Skill 必须在移交前完成 URL、参数、头、认证、断言、时长等作者配置。 |
| HTTP 身份 | `scripts/jmx.py:58–64,95–103` | HTTP 仅识别 HTTPSamplerProxy，线程组仅识别 ThreadGroup。结构路径形成请求 identity；新增 Skill 修改结构后需重新 prepare/确认，不能继续沿用旧 identity/hash。 |
| 前置作用域 | `scripts/jmx.py:113–126` | 前置必须是 HTTP，且与目标同一标准线程组、完全相同 ancestors、在目标之前。另一个线程组或另一个控制器中的登录请求不能直接声明为目标前置。 |
| 当前请求隔离 | `scripts/jmx.py:171–184,216–219`；`candidate/SKILL.md:27` | 每轮仅当前 HTTP + 已确认前置 HTTP 启用；不能要求先完成一个独立寻峰目标来留下登录态，再测试后一个目标。 |
| 标准结构与字面并发 | `references/supported-inputs.md:3–7`；`scripts/preflight.py:38–52` | 生成标准 ThreadGroup；并发须正整数字面 intProp/stringProp。scheduler=false 的 duration 不代表运行限制；不能以存在 duration 字段宣称试跑可自动结束。 |
| Runner 并发边界 | `scripts/jmx.py:130–132` | Runner 调整并发必须为正的 10 倍数。若新增 Skill 的预检采用 1 并发，不能直接调用 Runner 的寻峰运行接口冒充单次冒烟；静态输入原并发为 1 可以被识别，但拟生成的 Runner 运行并发 1 会拒绝。 |
| 内置配置 | `scripts/preflight.py:7–12` | HeaderManager、CookieManager、CacheManager、AuthManager、ConfigTestElement、CSVDataSet 在 SAFE。节点入白名单只是静态可接受，不证明其字段、作用域和认证行为正确。 |
| 内置断言/提取器 | `scripts/preflight.py:10–13,61–65` | ResponseAssertion、DurationAssertion、SizeAssertion、JSONPathAssertion，以及 Regex/JSON/XPath/Boundary 提取器在 SAFE。提取器与变量会产生需确认的依赖问题，不应据 HTTP 200 自动推定业务成功。 |
| setUp / OnceOnly / JSR223 | `scripts/preflight.py:7–12,53–60` | SAFE 未包括 setUpThreadGroup、OnceOnlyController、JSR223Sampler/PreProcessor/PostProcessor/Assertion。活动节点阻塞；disabled 节点的存在不证明它们一旦启用可运行。 |
| 确认不能覆盖 unsupported | `scripts/preflight.py:21–23,84–88` | 仅 kind=confirmation 的问题可由 confirmed_issue_ids 解除；unsupported 不因用户回答“确认”变成 ready。不可把平台不兼容伪装为仅待确认。 |
| Cookie 文件依赖 | `scripts/preflight.py:66–83`；`references/supported-inputs.md:8` | 已存在、绝对路径的 CSV 可避开相对布局检查；不存在文件或动态文件表达式仍阻塞。相对路径且副本目录改变必阻塞。代码不复制依赖、不改文件路径。 |
| 标签与报告 | `scripts/preflight.py:31–35`；`scripts/report.py:67–93` | 目标/前置标签须静态、非空、非 Total，启用集合不重名；否则 Statistics 会混并。目标报告行必须唯一且不是 controller，transaction 要与标签一致。 |
| 官方指标 | `scripts/report.py:67–116` | 按 5.6.3 的 statistics.json + index.html + dashboard.js 读取；验证 90th pct 的真实列名，不把平均值当 P90。只给出其他版本 JMX 或报告不能宣称已兼容。 |
| JMX XML 边界 | `scripts/jmx.py:67–105` | 要求 jmeterTestPlan、一个根 hashTree、元素/hashTree 成对、enabled 为 true/false；DTD/实体拒绝。这里未校验根 jmeter 版本属性，因此“XML 能解析”不是完整运行版本资格。 |
| 任务确认与执行入口 | `candidate/SKILL.md:16–25,54`；`requirements-v0.3.1.md:22–26,33` | 交给 Runner 时仍需本次许可、目标、输出目录、入口、源 SHA 和并发/质量确认。新 Skill 的试跑授权不能自动扩大为 6 轮寻峰授权。 |

## 认证方案的兼容矩阵

| 方案 | 与当前候选的关系 | 仍需决定/验证 |
|---|---|---|
| 工程师维护 CSV → CSVDataSet → 当前请求使用 Cookie 变量 | **静态上可设计为兼容**。CSVDataSet/HeaderManager 在 SAFE；文件须存在，绝对路径可绕开相对布局阻塞；变量需确认。 | CSV 列、编码、共享模式、EOF/recycle、每线程是否独立身份、过期检测、更新操作；不要在报告/模型摘要暴露 Cookie。 |
| 同作用域且在前的登录 HTTP → CookieManager → 目标 | **结构上有兼容路径**。两个 HTTP 同 ancestors 且顺序正确时可选为前置；CookieManager 在 SAFE。 | CookieManager 自动携带 Cookie 不等于持久写 CSV，不能悄悄替换用户的 CSV 要求；需确认登录是否每次迭代执行、登录负载是否污染目标情景、状态与成功断言、线程独立 Cookie 行为。 |
| 同作用域登录 HTTP → 内置提取器 → 变量/目标 Header | **结构上有兼容路径**；提取器与变量需确认。 | Set-Cookie 的多个值、Domain/Path/Expires、Token/CSRF、重定向；不得把单一正则匹配即当通用 Cookie 管理方案；仍未解决 CSV 持久化。 |
| setUpThreadGroup 登录 → 写 CSV → 主 ThreadGroup 读取 | **当前直接阻塞**。setUpThreadGroup 未资格验证，前置跨线程组不符合 selection。 | 若采用，需独立认证准备阶段或另外对 Runner 进行明确范围的资格扩展；不能在本次研究中视为已有支持。 |
| OnceOnlyController 内登录 → 同组目标 | **当前直接阻塞**，且不同 ancestors 不满足前置选择。 | 需要重新定义执行上下文/隔离语义和资格，不宜默认生成。 |
| 活动 JSR223/BeanShell 将 Cookie 写入 CSV | **当前直接阻塞**（不在 SAFE） | 共享文件并发写、原子性、覆盖/追加、权限和秘密保留均尚未设计；不能用一次 JMeter 成功退出解除该静态门。 |
| 独立认证准备 JMX/程序先写 CSV，再把兼容主 JMX交给 Runner | **可能的架构分层方案，尚未选定或验证** | 明确新增 Skill 的认证阶段与试跑阶段、谁更新文件、是否允许生成写文件脚本、哪个阶段取得目标许可；主 JMX 不引入写 CSV 节点，则可保留 Runner 当前边界。 |

## 最小验证边界（未来开发/真实试跑前的建议）

本节是方案建议，**本次未运行**。

1. **转换语义验证**：curl 只作为数据解析，不能直接由 shell 执行。核对 method/URL/query/header/body、转义与多行；列明被省略或重写的浏览器头。业务断言与凭据处理是待确认输入，不从参考样例臆造。
2. **静态 JMX 兼容验证**：新生成文件的结构、唯一静态标签、标准 ThreadGroup、scheduler/循环限制、活动节点、每个目标的 prerequisites、CSV 路径分别核对。通过兼容验证不等于完成业务试跑。
3. **认证行为验证**：使用无秘密的合成 fixture 验证 Cookie 接收/提取/携带、失效识别、重定向/多 Cookie/CSRF；若要求落 CSV，验证文件内容契约与并发写规则。当前未资格验证节点需要单列，不能藏入“正常脚本”。
4. **单次低负载试跑**：独立确认本次目标授权、请求集、并发、固定时长/循环、输出。若用 1 并发冒烟，使用新增 Skill 的有界一次执行设计；不复用 Runner 的多轮寻峰运行状态与预算。执行官方命令后核对真实退出、报告目标行、JTL失败/断言信息与日志，不能以到时/exit 0 当业务成功。
5. **移交兼容回读**：绑定最终主 JMX hash、目标 identity/label、明确前置、外部文件依赖和未闭合项。试跑后若再编辑 JMX，旧 hash/identity/试跑证据不继续冒充当前资格。Runner 后续按其自身任务确认执行。

## 对下一轮 Grill 的建议

优先确认认证架构：用户要求“登录并写 cookie.csv”时，究竟需要在**同一压测 JMX 中执行**，还是允许在**单独认证准备阶段**刷新 CSV，然后交付兼容主 JMX。该选择直接决定能否不改动既有 Runner，以及认证请求是否在每次迭代给目标系统增加负载。

随后确认新增 Skill 的“试跑通过”标准：至少同时区分 **官方 JMeter 可执行、业务请求/断言正确、Runner 静态可接收**。只满足其中一项不应自动移交寻峰。

## 仍未知的边界

- 本机当前真正安装/使用的 WorkBuddy Skill 版本与路径未核对；本文仅针对指定工作区候选。
- CSVDataSet 与 CookieManager 的具体字段/作用域组合未通过真实试跑；SAFE 不是行为证据。
- 登录接口的响应模型、Cookie/Token/CSRF、账号多并发许可、Session 排他性均未提供。
- 没有建立新 Skill 的默认请求头、超时、重定向、连接复用、断言规范或通过标准；需基于 curl 与工程师确认细化。
- 报告解析只核对候选代码支持的 5.6.3 布局；不推断其他 JMeter 版本/插件/语言模板兼容。
- 原有多个 ThreadGroup 的非 HTTP 节点不会由 enabled 白名单自动关闭；需要按实际生成结构检查作用域，不能把“当前一个 HTTP”表述扩展为“全部其他执行元素均禁用”。

## 2026-10-13 第二轮：同一 JMX 的认证组与业务组联动

本轮仅新增读取 `candidate/scripts/process.py`、`controller.py`、`contracts.py` 的代码证据。未执行代码、未读取真实 JMX、未改变第一轮证据。用户已确认会话共享与多账号均需支持、默认响应字段 `success=true`、三层通过、WorkBuddy / Windows / JMeter 5.6.3；不再把这些已确认事项写作待用户输入。用户关于“同一 JMX 不同线程组能否实现”的问句是方案讨论，不是升级现有 Runner 的开发授权。

### JMeter 能力与当前消费者能力必须分开

同一 JMX 的“独立认证线程组先生成 Cookie CSV，再由业务线程组读取”可以作为 JMeter 方案研究对象；这里核对的 Python 消费者**当前不支持直接接收该结构**。JMeter 自身的阶段顺序、Cookie 跨线程组传递及 CSV 分配方式需要官方文档/合成 fixture 佐证，不能仅凭 Python 的 XML 可解析性宣称通过。现有阻断不是 curl 转换器能靠生成技巧消除的。

| 当前行为 | 精确源码证据 | 架构影响 |
|---|---|---|
| 每个目标每一档都重新运行 JMeter | `controller.py:64–88` 外层 target、内层 while，每轮 prepare_copy 后调用 executor；`process.py:40–60` 每次 run_jmeter 都 Popen 并等待该子进程 | 不是长期 JMeter 实例里动态改线程数。JMeter 进程内 Cookie/变量不能凭前一轮继续存在；跨轮状态只能通过明确持久化产物或本轮重新认证连接。 |
| setUpThreadGroup 未被登记为标准组 | `jmx.py:58–64,99–103` 仅 tag=ThreadGroup 更新 group_id / groups；`selection:121–126` 要求标准组及前置同组同 ancestors | 正常根层 setUpThreadGroup 里的 HTTP 的 group_id 为 None；跨组认证不能成为当前目标 prerequisite。普通 ThreadGroup 认证虽有 group_id，也因不同 group 被拒绝。 |
| 所有未选 HTTP 都被禁用 | `jmx.py:117–127,171–184,216–219` | 仅把登录 HTTP 放另一个组但不声明前置，它会在运行副本里被关掉；声明为现有 prerequisites 又会被 selection 拒绝。 |
| 任一活动非 SAFE 节点均阻塞 | `preflight.py:24–26,53–60` | setUpThreadGroup 自身未 SAFE；写 CSV 的活动 JSR223 未 SAFE。不能仅新增“跨组前置”字段后就宣称可用。 |
| 所有目标必须在启动首进程前通过预检 | `controller.py:51–57`；`preflight.py:66–83` | 计划由本次认证组生成的 cookie.csv 若尚不存在，会先触发 missing-file；预先遗留文件通过存在性检查也不证明认证生成了本轮新文件。需要区分外部输入文件与运行阶段产出的依赖。 |
| JMeter cwd 是本轮副本目录 | `process.py:48–49`；`preflight.py:82–83` | 相对文件路径上下文真的改变，并非文档假设。生成者/消费者必须绑定同一个明确路径，或新增已验证的文件布局机制。 |
| 只给目标标签评分 | `controller.py:66–68,97–101`；`report.py:86–116` | 认证样本可作为独立标签保留在官方报告中；峰值继续只读目标 HTTP 行。认证失败还需要独立阶段判定，不能由某个目标恰好仍可访问而掩盖。 |
| 版本在运行入口实测 | `controller.py:49–50`；`process.py:64–71` | 实际调用 `-v`，仅 5.6.3 取得资格。这比第一轮仅报告解析限定 5.6.3 的证据更强；不扩展其他版本。 |

### 真正最小的联动修订面（尚未实施）

若选定同一 JMX 的 setUp 认证方案，至少涉及以下接口；**只给 SAFE 增加两个节点名不够**。

1. **解析与角色识别**（`jmx.py:39–64,87–104`）：保留现有业务标准 ThreadGroup；额外识别声明为认证的 setUpThreadGroup 和其 HTTP 身份。明确 group 类型/角色，不能让认证 HTTP 成为普通寻峰目标，不能把所有未知线程组泛化成已支持。
2. **任务配置的认证前置契约**（`controller.py:18–35,51–57`、`jmx.py:113–126`）：当前 target.prerequisites 表示同组同作用域的 HTTP，不能悄悄改成任意跨组请求。新增明确的阶段认证引用与 Cookie 产物依赖，普通业务前置继续沿用原约束；描述本轮认证请求集合、依赖的账号集/会话共享模式。
3. **复制与独立差异校验**（`jmx.py:158–189,192–227`）：启用集合变为“当前业务 HTTP + 普通已确认前置 + 当前所需认证 HTTP”；认证组并发/循环等沿用新 Skill 生成且已确认的原配置，不能自动随着业务并发变成 50/100/200/500。若确需改组 enabled、文件路径或其他属性，要另列精确允许变化与独立验证；不能放宽整份文档 signature 比较。
4. **SAFE 与执行上下文资格**（`preflight.py:7–12,24–30,53–65`）：仅资格验证固定的 setUp 认证模式和受控写文件机制。不要把任何任意 JSR223/BeanShell 代码整体加入 SAFE。脚本所属节点、作用域、执行次数、写入目的地应可验证，禁用祖先与业务隔离继续检查。
5. **运行生成文件依赖**（`preflight.py:66–83`、`controller.py:51–57,77–101`）：对工程师手工 CSV 仍要求启动前存在；对声明由本轮认证产生的 CSV，可验证生成者/消费者关系及路径，而不能以旧 CSV 存在通过。运行时必须确认认证成功和新产物完整后才发业务请求。原子提交、失败不回退使用旧 Cookie、账号行映射和本地敏感内容边界都是该依赖契约的一部分。
6. **每轮认证的生命周期与故障传播**（`controller.py:70–116`、`process.py:40–60`）：同一 JMX 随每轮新进程启动，通常意味着每档重新执行认证阶段。若需求是“整次任务只登录一次”，需要另一个明确生命周期，不能默认认为 setUp 在整个六轮任务只发生一次。认证失败必须阻止依赖业务发压并记为准备/认证技术问题，不当作目标容量失败；不自动重发，保留剩余目标是否依赖同一认证产物的判断。
7. **标签、官方报告与交付**（`preflight.py:31–35`、`report.py:67–116`、`controller.py:66–68,97–112`）：认证与业务标签均唯一且静态，仍只读业务目标行做 TPS / P90 / 错误率评分。官方 report Start/End 是整次执行的 General Infos，加入认证阶段后可能覆盖认证时间；不修改它伪装成业务采样起止。可额外记录认证阶段证据，但不得重算或替换官方字段。
8. **最小回归范围**：原有同组前置与无认证脚本应保持行为不变；追加 setUp 角色识别/拒绝未声明组、精确 HTTP 启用集合、源 SHA/副本差异校验、文件新生成与失败残留、跨组身份映射、认证失败阻断、多账号/会话共享、CSV EOF/复用、目标唯一标签及官方指标选择。重点覆盖新契约和直接关联模块，不要求全量重跑寻峰算法或历史宿主实验。

### 默认断言与认证数据的作用域

已确认的默认 `success=true` 应进入生成脚本规范和试跑验证，不再为默认值主动追问。但认证与业务响应需分别验证，断言应落在对应 HTTP Sampler 下，避免一个全局 JSON 断言错误作用到不返回该结构的辅助请求。字段缺失、false、类型不符、空响应应有清楚失败记录；接口实际不是此契约时，在转换/试跑结果中记录不匹配，再补充信息。

多账号不等于必须让每个并发线程有独占账号：用户已要求支持会话共享，账号行数、业务线程对账号行的映射及 CSV EOF 策略必须与选定模式一致。CSVDataSet 的静态 SAFE 不能证明这些运行语义。没有经过明确策略与 fixture 验证，不能让 EOF 字面值、空行或旧 Cookie悄悄参与性能测量。

### 建议的架构判断

- **同一 JMX 可继续作为候选方案研究**：优先明确 setUp 认证阶段与业务标准线程组，而非普通两个 ThreadGroup 并行启动；后者至少还需证明先后顺序和文件读写屏障。
- **当前直接可用方案与升级方案分栏**：当前消费者直接可用的是静态兼容主 JMX + 已存在且可定位的 Cookie CSV；同一 JMX 自认证/产出 CSV 属于需联动修订并资格验证的候选。
- **三层通过按用户确认执行**：官方 JMeter 可执行、业务/认证断言正确、Runner 可接收三层都成立才能移交；纯 JMeter 冒烟不解除上述消费者阻断。
- **授权状态**：本轮只完成研究与 Grill 资料补充；没有将问句视为开发批准，没有扩大已有 Runner 的生产输入或节点支持范围。

