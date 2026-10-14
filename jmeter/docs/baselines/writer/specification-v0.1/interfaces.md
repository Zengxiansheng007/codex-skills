> 公开投影：业务规则与原编号保留；“本轮”指源文档编写阶段。源哈希、路径适配与当前发布范围见 jmeter/docs/publication-context.md 及导出清单。

# 接口与数据契约 v0.1

日期：2026-10-13。状态：拟定规格，不是已实现的 CLI / Schema。配合 [主规格](spec.md) 阅读。覆盖 REQ-001–007 / AC-001–007；准确写集见 [改动范围](change-scope.md)。

## 1. 公开入口

首期使用固定本地 CLI、UTF-8 JSON 文件参数与结构化结果。Agent 不通过自由拼接 XML、修改任意字段或执行收到的 cURL 完成任务。入口名称为拟定名称。

| 接口 | 输入 | 输出 / 副作用 | 重要边界 |
|---|---|---|---|
| writer analyse | 来源 cURL / 已有 JMX、目标、正式参数、会话/认证材料 | 分析结果、缺项、支持差异、目标/前置建议；只读输入 | 不执行 Bash，不登录、不运行业务；只有不确定信息才补问。 |
| writer build | 足够的分析材料与编写决定 | 新正式 JMX、角色/依赖描述、模板与编写差异 | 正式 Ramp-up / 时长来自工程师；已有 JMX不重建、不擅改头或断言。 |
| writer probe-auth | 登录请求材料、一个验证账号、当前任务授权 | 最多一次预登录的实际结果与提取依据 | 仅缺少提取依据时使用；与完整试跑分开计数，失败不重试。 |
| writer validate | 明确最终原件、目标、依赖、一个会话、JMeter 和消费者、当前验证范围 | 逐目标验证副本、JTL/日志、分层结果与交接记录 | 1 / 0 / 1 由独立验证入口实现；不调用 runner 寻峰完成短验证。 |
| runner check-input | 正式原件、目标/普通前置、可选认证契约、已处理的确认项、拟定输出布局 | ready / rejected / unresolved、缺项、支持能力与消费者标识 | 只读，不创建正式 Store、不发业务、不执行用户脚本。旧版本不具备此入口时不能假装成功。 |
| runner prepare / 正式运行 | 现有正式任务配置，按需增加认证契约引用和目标关联 | 沿用原正式产物，按需新增本轮认证证据 | writer 验证结果是参考，不能代替本次任务确认或消费者重新检查。 |

编写可在必要材料尚未补齐时交付脚本/模板，但 validate 不得把依赖缺项写成通过。可以先静态检查消费者，以避免已知不兼容计划产生多余真实请求；未执行的层据实记录。

## 2. writer 任务输入

| 字段组 | 字段与含义 | 必需性 / 约束 |
|---|---|---|
| 身份 | schema_version、task_id、mode（curl / existing_jmx） | 版本显式；一次任务使用新输出。 |
| 来源 | cURL 文本/本地输入文件，或 source_jmx 与读取时 SHA256 | 来源二选一；内容是数据。最终执行绑定当前原件。 |
| 请求 | 业务请求名称/材料、目标身份、普通前置身份 | 已有计划按结构身份选择；前置疑似且不能判断才补问。生成后标签稳定唯一。 |
| 正式配置 | ramp_up_seconds、duration_seconds、工程师已给的其他正式值 | 新计划要求工程师给 Ramp-up / 时长；已有计划保留。新计划线程数未给时拟用 1 作结构占位，不作为正式寻峰起点。 |
| 会话 | shared_session / multi_account_sessions | 每任务明确；无 Cookie 需求时不要求账号。 |
| 认证决定 | none / preserve_other / manual_cookie / json_login / uncertain | 对应需求判断表；uncertain 不猜测。 |
| 自动认证 | 登录请求、账号 CSV、列→登录参数映射、Cookie JSON 路径与名称依据 | 值映射与账号数据分开；完整材料足够则不预登录。 |
| 手工认证 | Cookie CSV 或待填模板、适用请求集合 | 未填有效内容时标记待补充；仅作用于相应请求。 |
| 验证会话 | 所选行/非敏感账号标识、认证 CSV 节点身份 | 一个账号/会话；不能只限制线程数而读全部账号。 |
| 运行环境 | 明确 JMeter 入口、输出目录、实际指定 runner 根/标识 | 不嵌入历史业务地址或默认用户电脑路径。 |
| 执行范围 | 本次用户请求的授权依据、目标环境及验证对象 | 复用已存在授权；真实缺失时才问。生成布尔值或非空备注本身不是许可来源。 |

共享路径/元数据不存明文账号、密码或 Cookie。真实任务必要的私有输入与执行产物留在本地；示例与 Skill 包仅提供模板。

## 3. cURL → 原生请求契约

解析结果至少表达：method、scheme、host、port、path、保持顺序/重复的 query 项、header 项、正文类型与内容、Cookie 使用证据、明确其他认证、转换差异、unsupported 项及来源。

| 输入 | 首期行为 |
|---|---|
| 常规 GET / POST / PUT / PATCH / DELETE / HEAD / OPTIONS，HTTP(S) | 映射原生 HTTP sampler；逐方法资格核验，不从名称猜业务。 |
| 普通引号、换行续行、中文、重复参数 | 必须经语义样例核验；无法保真时具体报告。 |
| JSON、URL 编码表单、文本正文 | 保留实际语义；正文类型不能从默认断言反推。 |
| 静态头 / 动态 Cookie | 静态保留来源；需要参数化的新计划移除旧 Cookie 覆盖，动态引用仅对适用请求生效。 |
| cURL 认证、重定向、压缩等选项 | 仅接受经过映射资格验证的选项；不能默默采用 JMeter GUI 导入默认值代替来源。 |
| 上传、@外部正文、复杂 Shell / 命令替换、未资格传输选项 | 报具体不支持/差异，不执行、不下载外部正文、不静默忽略。 |
| 字面 JMeter 变量/函数表达式或可能被解释的内容 | 必须保真转义并核对，不把数据插入可执行表达式；未资格则拒绝相应转换。 |

优先复用 5.6.3 BasicCurlParser 与 Request 模型，通过本地小适配器生成原生元素。无头初始化、JMX 序列化、支持语法和 JMeter 字面转义是技术资格门 G-01；此处不声称官方已有无头 CLI。

## 4. 新计划与已有计划

### 新生成计划

- 标准业务组按实际认证/头作用域组织；动态头不能泄漏到无需 Cookie 的请求。组数不是业务需求，不以美观统一分组。
- 自动认证使用 SetupThreadGroup（5.6.3 官方保存别名已核对），业务目标仍为标准 ThreadGroup 下的 HTTPSamplerProxy。
- 每个业务目标默认 JSONPathAssertion：路径 $.success、期望 true，沿用原生组件匹配语义；不新增严格 JSON 布尔类型承诺。
- 业务循环采用明确调度时长；正式值保留工程师输入，不使用历史 120 / 180 秒。
- 新 Cookie CSV 的建议格式：UTF-8 无 BOM、含表头、单列 cookie，值为完整 Cookie 请求头；原生 CSV 引用变量 cookie。
- 新 CSV 显式 Recycle=true、Stop thread=false、Sharing=All threads；引用与 CSV 引号/编码一致。

### 已有计划

保留原件和已有业务头/断言/CSV 配置。结构身份、依赖、认证范围明确后才能验证。缺业务断言仅提醒；真实失败仍失败。不符合消费者契约时说明缺项，不通过重建 JMX 或改写原件伪造兼容。

## 5. 身份、角色与认证描述

增加非秘密的 AuthContract v1，作为正式 JMX 的旁文件。它不是可执行脚本，不通过文件名或 HTTP 名称猜角色。

| 字段 | 含义 / 校验 |
|---|---|
| schema_version、source_sha256 | 只绑定对应原件；源变化需重新分析，不使用失效角色。 |
| stages[].stage_id | 稳定非秘密标识；用于属性/产物命名，不接受任意路径片段。 |
| group_identity、http_identities | 认证组与其必要登录 HTTP 的结构身份。认证 HTTP 不成为业务目标。 |
| account_csv_identity / input_reference / format | 原生账号 CSV 节点、输入与实际列格式；不含秘密值。 |
| formal_account_count | 与正式配置、认证有限循环及当前账号输入一致；账号规模变化不得静默沿用旧循环。 |
| extractor_bindings | 原生 JSON 提取器身份、变量及 Cookie 名来源。 |
| template_bindings | 仅固定前/后处理模板 ID、确切摘要、节点身份、限定参数；摘要并非对任意脚本的安全背书。 |
| producer / consumer_bindings | 哪个阶段生成 Cookie，哪些 CSV 节点读取哪个限定进程属性。 |
| applicable_target_ids | 目标到必要认证阶段的精确关联；不向全部业务目标自动附登录。 |

目标选择仍使用现有普通 prerequisites 字段；新增 authentication_stage_ids 只关联已声明认证阶段。普通前置的同组、同执行上下文、先于目标约束保持。没有自动认证声明时走旧路径；发现活动自动结构但没有可核契约时拒绝，不能默认绕过。

## 6. 固定认证构件与本轮 CSV 产物

以下是待实测的具体设计，不是已通过的运行机制。

### 认证组

正式新计划：一个认证线程、Ramp-up 0、账号数 N 对应 N 次原生主迭代。原生账号 CSV 为每次登录提供行值；不自研线程身份/账号分配器。短验证副本把该阶段的必要循环改为 1，并仅把对应认证输入 CSV 引用替换为所选单行数据。

固定初始化前处理、JSONPostProcessor、固定收集/发布后处理均附着在登录 HTTP 下。登录被禁用时这些构件不独立运行，不新增辅助 sampler 启用权限。登录组错误采用计划内停止本测试的语义；业务组正式错误策略按已给配置保留。

后处理核对协议样本、Cookie 提取有效性、累计数与发布结果。后处理可能先于断言运行，因此“CSV 已发布”不能单独证明认证断言通过；最终还必须核对实际登录样本的成功/断言状态。

### 目录与发布

- 用 FileServer 的执行计划基准和当前 JMX 文件名定位同目录下的保留产物名，例如 run-001 的 stage-a Cookie 与认证结果；不同 run 文件名必须得到不同产物。
- 账号/手工输入与生成产物分开，固定构件不能写回工程师原始文件。
- 先准备临时完整 Cookie CSV，全部 N 个账号取得有效值且数据关闭后才发布最终文件；失败不发布部分成功、不回退旧文件。
- Cookie CSV 与认证结果都只在固定保留命名范围内写入。无法完成发布则使认证失败，不改写其他路径。
- 初始化清理/失效仅限该次声明的生成产物，不能删除输入或其他轮产物。每进程属性绑定也重新建立，不继承旧值。
- 固定构件把最终绝对路径发布到限定 JMeter 属性；业务原生 CSV filename 仅允许对应 __P 属性表达式，缺值没有旧文件默认值。
- 这一表达式是生成依赖的特例，不是任意动态文件放行。静态输入继续原有存在性/布局检查，生成文件则核对生产者、属性、消费节点、基准和运行后证据。

FileServer / 属性解析与无关线程组的原生 CSV 行为必须通过 G-02 真实资格测试。若实现无法在原正式副本白名单内满足精确隔离，应记录失败并修订生成结构；不能擅加线程组 enabled 或脚本修改权限。

### AuthenticationResult v1（本轮）

| 字段 | 作用 |
|---|---|
| schema_version、stage_id、execution_plan_name | 对应契约、阶段及本轮 JMX；不能来自其他轮次。 |
| status | preparing / complete / failed；complete 只在完整产物发布后写。 |
| expected_account_count、prepared_account_count | writer 试跑为 1；正式模式为当前 N。必须一致才完成。 |
| cookie_artifact / sha256 / row_count | 对本轮 CSV 的身份、完整性及计数，摘要不含实际 Cookie。 |
| template_id / template_sha256 | 与已资格构件对应。 |
| failure_code / safe_detail | 明确阶段错误，不输出秘密值，不凭响应码推断账号为何错。 |

可信条件是组合证据：声明绑定、生成目录/命名、真实退出、本轮 Cookie 完整性、实际登录样本及目标执行。文件存在、文件时间、一个 complete 字段或哈希一致都不能独自替代认证成功。

## 7. 验证副本允许变更

| 对象 | 允许变化 | 必须保留 |
|---|---|---|
| 当前标准业务组 | num_threads=1、ramp=0、scheduler=开启、duration=1、使此调度生效的循环配置 | 正式原件、业务请求参数、已有 timer / 头 / 断言 / 非必要调度属性 |
| 对应认证组 | 为所选一个账号所需的线程/循环配置；生成式认证以 1 个账号执行 | 原件 N 个账号准备逻辑、提取与固定脚本文本 |
| HTTP samplers | 仅当前目标＋必要登录＋已确认普通前置启用 | 非 HTTP 任意 enabled / 组 enabled 不因此获得变更权限 |
| 认证 CSV | 创建单账号/单 Cookie 数据，替换对应 filename 引用 | 原文件、列名/变量、编码、表头、引号、EOF、共享策略 |
| 其他 | 不允许 | 静态头、正文、URL、断言、脚本、无关文件与结构 |

生成与独立校验是两个动作。校验从原件和副本重新解析，按精准节点/字段屏蔽可改项，其他完整结构/语义必须一致。原始文件摘要在执行前后再核对。

1 秒内允许多个样本，不限制为一次循环替代 duration。没有样本、认证未完成或未知结束都不能报通过。当前子进程结束并核出验证失败后，不启动后续目标，不自动修正/重试；不新增专门超时强停模块。

## 8. runner 接收扩展

### 只读 check-input

返回 consumer_identity（实际根/版本/包标识/协议能力）、source_sha256、逐目标 ready 状态、普通前置、认证阶段、精确 HTTP 选集、静态输入/生成依赖及 blocking / confirmation 问题。输出布局作为检查参数；不落正式任务、不启动业务。

旧确认项不能放行 unsupported；认证结构、脚本参数、源 hash 或依赖变化后重新核对。未知消费者只记未验证；已知明确拒绝则兼容失败。

### 正式任务扩展

可选 auth_contract_ref 与 auth_contract_sha256；每个目标新增可选 authentication_stage_ids（无认证时空）。已有字段、单位、确认、10 的倍数并发、6 轮预算及 3% 触发保持。

每轮：
1. 精确验证正式副本，仅允许目标组并发及 HTTP enabled 变化。
2. 按当前 plan 路径派生本轮认证产物预期；不写 CSV 路径到正式副本。
3. 官方 JMeter 执行完整计划。先 setUp，后目标业务。
4. 真实结束后核认证结果、Cookie / 登录样本，再读目标官方 Statistics。
5. 认证失败为本目标技术问题：保留已启动轮、无合格候选贡献、不重发，沿用后续目标推进与问题队列。
6. 认证/前置样本不混入目标指标；report 官方时间窗口不人为修改。

已有问题等待和结束展示机制保持，不由 writer 改造。

## 9. ValidationResult v1 与总体交接

每目标记录：结构身份/名称、验证账号的非秘密标识、原件/依赖摘要、副本/差异、实际 JMeter 环境、命令参数与真实执行结束、实际目标样本、认证结果、断言结果、指定消费者及证据引用。

三层分别为：
- execution：passed / failed / not_tested / unknown；目标样本与实际结束必查。
- authentication：passed / failed / not_applicable / not_tested；有需要时只覆盖所选账号。
- assertions：passed / failed / absent_legacy / not_tested；absent_legacy 明确“业务断言未验证”。
- consumer：accepted / rejected / unresolved / not_tested；必须对应实际指定版本，不能采用原型预期。

总体状态：
1. 有真实执行/认证/已配置断言失败或明确消费者拒绝 → failed。
2. 必需材料不足 → needs_input；未覆盖/未知层 → unverified。
3. 所选全部目标的必需检查满足，只有既有缺业务断言提醒 → ready_with_warning。
4. 所选全部目标适用检查满足 → ready。

一条目标通过不代表整份未选请求、其他账号或其他环境通过。报告列出 selected / validated / not_tested，并给出原因和建议。命令退出码与产品状态分别记录：命令处理结束或 child exit 0 不是就绪依据，调用方必须读取结构化状态。

## 10. 最小交付

正式 JMX；AuthContract（自动模式）；手工模板 / 必要本地依赖与填写说明；逐目标验证副本及原始 JTL / 日志；中文结论与 ValidationResult；实际消费者标识和未验证范围。

可分享说明/包没有真实 cURL 秘密、账号、密码、Cookie 或私有响应体。用于核验的私有原始证据与可分享摘要分开；已有脚本的保存配置不为此被擅自重写。

## 11. 固定调用形式、类型与错误输出

拟定入口仅接收任务文件：
- writer analyse / build / probe-auth / validate：统一 --task 参数；任务文件中给出明确输出根。cURL、凭据、Cookie 不通过命令行参数传递。
- runner check-input：--request 指向只读消费者检查文件。
- runner prepare / run：原参数保留；自动模式通过可选认证契约字段传递，不另起 writer runtime。

入口可用固定脚本绝对路径从任意 cwd 调用；任务内相对输入以该任务文件目录解析，并在结果中记录实际解析位置。输出须全新、位于 Skill 目录之外。Shell 只是传递文件路径，不解释收到的 cURL。

TaskInput v1 的拟定机器字段：

| 根字段 | 类型 | 最小约束 |
|---|---|---|
| schema_version | string | 固定协议版本 writer-task-v1，不静默忽略未知版本。 |
| task_id / mode | string / enum | mode 为 curl 或 existing_jmx。 |
| source | object | cURL 输入引用/文本，或 jmx_path 与 source_sha256；与 mode 对应。 |
| requests | array | 新请求逻辑 ID / 名称 / 材料；已有输入最终使用源绑定的 XML 结构 ID。 |
| formal | object | 新计划 ramp_up_seconds 为非负整数，duration_seconds 为正整数；可选工程师提供的原件线程字段。 |
| authentication | object | mode 为 none / preserve_other / manual_cookie / json_login / uncertain；条件字段参照前文。 |
| authentication.cookie_mappings | array | 每项 JSON 路径、输出变量及 Cookie 名/完整头值模式；只保存映射，值留私有数据。 |
| authentication.account_input | object | 本地 CSV 引用、列格式、账号字段映射；共享模式准备一账号，多账号准备当前 N。 |
| trial | object | target IDs、明确普通前置、认证绑定、单验证行/会话引用。配置固定业务 1 / 0 / 1，不接收任意寻峰参数。 |
| runtime / consumer | object | 明确 JMeter 入口，实际消费者根/版本/协议身份；未知标未验证。 |
| output_dir | string | 新任务目录，不覆盖旧任务或 Skill。 |
| authorization | object | 本次真实请求/既有授权的依据及环境范围；不是自行生成的许可。 |

分析/编写输出包括 source / generated_plan、request_mapping、dependency_inventory、conversion_differences、questions_required、warnings 和 evidence_refs。验证输出增加 target_results、overall_status、validated_scope、not_tested_scope 及修正建议。

统一结果可被处理时，命令层 exit 0 只表示结果已产生，domain overall_status 仍可能是 failed / needs_input / unverified。内部异常无法形成可信完整结果则非零，并保留安全诊断；参数/协议错误不启动 JMeter。SKILL 和调用者必须解析整体状态，不以退出码自动继续。

consumer-check 请求字段：schema_version、source / source_sha256、targets（id、prerequisites、authentication_stage_ids、confirmed_issue_ids）、可选 auth_contract_ref / sha256、拟定输出布局。返回不附带正式 task_id 的执行许可，也不创建正式任务状态。

所有字段名是本规格的拟定接口，不宣称当前 runner 已实现。实际 schema 校验拒绝条件、默认值和未知字段策略应由入口测试证明；不能因兼容保留旧字段而接受未知脚本/角色。


