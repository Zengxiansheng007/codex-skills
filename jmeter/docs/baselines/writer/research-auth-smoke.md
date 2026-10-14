> 公开投影：业务规则与原编号保留；“本轮”指源文档编写阶段。源哈希、路径适配与当前发布范围见 jmeter/docs/publication-context.md 及导出清单。

# cURL → JMeter 脚本准备：认证、请求规范与试跑研究

查证日期：2026-10-13。研究代理采用 matt-research；仅检索一手技术资料、读取本地技能约定并生成本说明，未运行 JMeter、未安装依赖、未访问业务目标、未接触账号或真实 Cookie。本说明用于需求讨论，不代表用户已接受其中的建议。

## 结论

两个核心能力可以沿用 JMeter 原生构件与官方 CLI；难点在于确定成功标准、会话模型以及交给现有 runner 的兼容边界。cURL 提供请求样例，不能独自证明接口业务成功、动态参数来源或会话可持续使用。

用户要求的“登录后写 cookie.csv”是一个独立认证准备能力。HTTP Cookie Manager 自动维护内存 Cookie、将 Cookie 暴露为线程变量、导出一个可供下一次运行读取的 CSV，三者不能混为一谈。建议优先讨论“独立登录准备计划 → 本地程序生成 CSV → 业务 JMX 消费 CSV”，同时明确单账户共享会话还是多账户独立会话。

## 1. 已核实的原生能力

### F01：JMeter 已有 cURL 导入器，但还不是完整性能脚本生成器

JMeter 官方说明 Tools → Import from cURL 可从文本或文件导入多条命令，生成 HTTP Sampler；被忽略或存在警告的内容会写入 HTTP Request 的注释。转换后仍需确定认证、关联、断言与负载配置。[Apache JMeter：cURL](https://jmeter.apache.org/usermanual/curl.html)

官方 JMeter cURL 页面中数据选项的标签/描述存在重复与混乱；不能照抄为转换规则。例如 curl 官方明确 `--data-raw` 不把开头 `@` 解释成文件读取；`--data`、`--data-binary` 与 URL 编码选项的语义也不同。`-H` 可重复，空值删除内部头与发送空头的写法不同；`-X` 与重定向组合也有独立行为。因此实现需要选项支持表和转换样例测试，保留警告，不能把任意 Bash 命令直接执行来“解析”。[curl 官方手册](https://curl.se/docs/manpage.html)

**建议而非已确认要求：**首期以浏览器复制的 HTTP/HTTPS cURL 为输入；支持的方法、正文形式、引号/转义与文件依赖明确列出。检测到 shell 管道、命令替换、外部文件、签名参数、客户端证书或转换器不支持的选项时，应保留原义并指出待处理项，不静默删去。

### F02：默认 HTTP 成功不能替代业务断言

JMeter 5.6.3 的 HTTP Sampler 将 200–399 视为默认成功区间；这并不检查 JSON 中的业务码、是否被重定向到登录页或业务对象是否有效。[Apache 源码：HTTPSamplerBase，rel/v5.6.3](https://raw.githubusercontent.com/apache/jmeter/rel/v5.6.3/src/protocol/http/src/main/java/org/apache/jmeter/protocol/http/sampler/HTTPSamplerBase.java)

Response Assertion 可校验响应状态、内容等；`assume_success` 默认 false，开启后源码会先把样本改为成功，因此不能无理由开启来掩盖 HTTP 错误。[Apache 源码：ResponseAssertion，rel/v5.6.3](https://raw.githubusercontent.com/apache/jmeter/rel/v5.6.3/src/components/src/main/java/org/apache/jmeter/assertions/ResponseAssertion.java)

JSON JMESPath Assertion 会解析 JSON，并检查表达式结果及可选期望值；它适合用户给定的业务字段。JMESPath Extractor 则用于关联，提取不到或异常时可能写默认值，不等于断言失败；需要另外检查必需变量并防止错误值继续作为认证或请求参数。[Apache 源码：JMESPathAssertion](https://raw.githubusercontent.com/apache/jmeter/rel/v5.6.3/src/components/src/main/java/org/apache/jmeter/assertions/jmespath/JMESPathAssertion.java)、[Apache 源码：JMESPathExtractor](https://raw.githubusercontent.com/apache/jmeter/rel/v5.6.3/src/components/src/main/java/org/apache/jmeter/extractor/json/jmespath/JMESPathExtractor.java)

**推论与建议：**同一请求至少区分“期望 HTTP 状态”与“业务成功条件”。成功响应示例可以帮助 AI 提出候选断言，最终业务条件需要工程师或接口规范确认。HTTP 200 且 `success=false`、200 登录页、空结果合法等情况不能由 AI 自行定义。P90 是轮次聚合指标；不要默认增加逐样本时长断言并把慢响应混进业务错误率。

### F03：请求头需要按请求语义规范化

5.6.3 HttpClient4 实现拒绝用 Header Manager 覆盖 Content-Length；Host 有专门处理；先处理普通头，再由 Cookie Manager 在存在适用 Cookie 时设置 Cookie；POST 正文未给 Content-Type 时可落入表单默认类型。以上都是请求复现时需要核对的机制。[Apache 源码：HTTPHC4Impl，rel/v5.6.3](https://raw.githubusercontent.com/apache/jmeter/rel/v5.6.3/src/protocol/http/src/main/java/org/apache/jmeter/protocol/http/sampler/HTTPHC4Impl.java)

Header Manager 源码按不区分大小写的头名处理合并，合并实现保留当前已有同名项；不能把重复请求头无条件压成普通字典，也不应仅靠多个作用域的继承顺序推断最终值。[Apache 源码：HeaderManager，rel/v5.6.3](https://raw.githubusercontent.com/apache/jmeter/rel/v5.6.3/src/protocol/http/src/main/java/org/apache/jmeter/protocol/http/control/HeaderManager.java)

**建议的默认规范（待用户确认）：**

| 头部/配置 | 建议处理 | 理由与边界 |
| --- | --- | --- |
| Content-Length | 不固化抓包数值；由请求实现计算 | 参数化正文长度会变化；上述实现拒绝覆盖 |
| Host | 普通请求按目标 URL；显式自定义 Host 单列确认 | 虚拟主机/路由测试可能依赖它，不能统一删除 |
| Content-Type | 保留与正文一致的类型，缺失时根据实际正文与接口规范确认 | 不能给所有请求统一添加 application/json；multipart boundary 应由构造正文的工具协调 |
| Accept、Authorization、业务自定义头 | 保留真实必要项；认证值外部引用 | 这些可能改变接口语义 |
| Cookie | 明确选择 CSV 固定 Cookie 或 Cookie Manager 管理 | 避免两个来源互相覆盖 |
| User-Agent、Origin、Referer、浏览器提示头 | 检查服务是否依赖，展示删减依据 | 不承诺删掉后一定等价，也不伪造默认浏览器身份 |
| Connection、Accept-Encoding | 与 KeepAlive/压缩配置一起核对 | 不与请求实现配置互相冲突 |
| 重复头 | 保留输入顺序与重复证据，按字段语义处理 | 不能静默最后一项覆盖全部 |

建议先生成逐请求的最终有效头表，再写入 JMX；共同头可以在生成模型中复用，但最终请求的有效值必须可解释、可核验。

## 2. Cookie 与登录准备的事实边界

### F04：线程内 Cookie 管理不等于 Cookie CSV

HTTP Cookie Manager 会保存服务端 Cookie 并在后续适用请求中发送；每个线程有独立 Cookie 存储区，手工静态 Cookie 则可供所有线程使用。`CookieManager.save.cookies=true` 把值暴露为 `COOKIE_` 开头的线程变量；其 Save As 并不保存从 HTTP 响应获得的运行 Cookie。[Apache JMeter：HTTP Cookie Manager](https://jmeter.apache.org/usermanual/component_reference.html#HTTP_Cookie_Manager)

5.6.3 源码进一步确认：收到 Cookie 后写入当前线程变量；`save()` 是静态 Cookie 文件导出，采用七字段制表分隔格式，包含 domain/path/secure/expires/name/value。这不是用户指定的逗号 CSV，也不是自动响应 Cookie 导出契约。[Apache 源码：CookieManager，rel/v5.6.3](https://raw.githubusercontent.com/apache/jmeter/rel/v5.6.3/src/protocol/http/src/main/java/org/apache/jmeter/protocol/http/control/CookieManager.java)

curl 的 cookie jar 同样采用 Netscape 文本格式，而 `Cookie:` 请求头只有名称和值；文件名字叫 cookie.csv 不会令这些格式自动互换。[curl：HTTP Cookies](https://curl.se/docs/http-cookies.html)

**推论：**新的 JMeter 进程不能自然继承上一进程的线程 Cookie 存储。若要跨“登录准备 → 试跑 → 多轮寻峰”使用，必须明确重新登录或文件/其他持久化传递，不可依赖内存自动延续。导出的 CSV 若只保存完整 Cookie 请求头，将缺少浏览器 Cookie jar 的完整作用域与有效期信息；至少要在旁附配置中绑定环境/允许域名并定义过期处理。

### F05：多 Cookie 必须维持作用域与账号关系

HTTP Cookie 规范区分 Set-Cookie 与 Cookie；Domain、Path、Secure、Expires/Max-Age 影响保存与发送。多个 Set-Cookie 不能简单用逗号拼为一个头，因为 Expires 本身可以包含逗号。[HTTP Working Group：RFC 6265](https://httpwg.org/specs/rfc6265.html)

**建议：**不要只用“取第一个 Set-Cookie”正则。先用 JMeter 原生 Cookie Manager 解析，再由独立导出程序依据所选目标 URL、允许域名和账号键生成 CSV。导出后核对必需 Cookie 的存在，并对未成功账号保留失败清单；不把全部响应头、密码或真实 Cookie 写进研究文档/日志/分享包。

### F06：CSV Sharing Mode 不自动保证账号与线程绑定

CSV Data Set Config 在 `iterationStart` 取行并把列写入当前线程变量。共享模式区分全线程、当前线程组、当前线程及标识键；共享的是文件读取游标。EOF 可以回卷；不回卷时可停止线程，否则变量变成 EOF 标记。相同文件不同引用也可能产生不同游标。[Apache 源码：CSVDataSet，rel/v5.6.3](https://raw.githubusercontent.com/apache/jmeter/rel/v5.6.3/src/components/src/main/java/org/apache/jmeter/config/CSVDataSet.java)

**推论与待定设计：**

- 单行 Cookie + 回卷意味着多线程可能共享一个会话。可以是有效测试模型，但必须说明这是单会话多并发。
- 多账户 CSV + All threads 不能直接保证每个线程一直用同一个账号；多次迭代会继续取行。
- Current thread 让各线程有独立游标，不表示各线程自动选中不同首行。
- “最大并发大于账号行数”的行为必须确认：重复账号、补充账号、限制并发或停止，不可默认回卷并宣称独立用户。
- 如果首期需要账号与线程固定绑定，须设计一次分配、保持稳定的消费机制，再核对 runner 支持范围；仅设置 Sharing Mode 不能完成这一需求。

### F07：登录位置决定负载及兼容性

setUp Thread Group 在普通线程组之前执行，但变量仍是线程本地；跨线程组共享需要明确属性或文件传递。JMeter 官方也给出账号密码 CSV 的参数化模式，并建议负载测试少用监听器、选择 CLI、减少断言与脚本开销。[Apache JMeter：Best Practices](https://jmeter.apache.org/usermanual/best-practices.html)

本次本地兼容代理确认：现有候选 SAFE 不包含 setUpThreadGroup、OnceOnlyController、JSR223；未知激活构件会被预检拒绝。前置请求必须属于标准同线程组、同祖先且顺序在目标之前。证据：preflight.py（历史本地参考，未随本次导出） 的 SAFE 与未知激活项校验，jmx.py（历史本地参考，未随本次导出） 的前置关系校验；详见同目录 `research-runner-compatibility.md`。这里区分 JMeter 原生支持和现有消费者支持，未自行复验候选源码。

**推论：**直接在业务 JMX 放一次登录控制器/JSR223 导出会触发现有兼容限制；把登录请求放在普通重复循环里，则可能每个目标迭代都登录，改变负载。若要每线程首次登录，需要正式扩展 runner 支持及验证，不能只修改新 Skill 并宣称兼容。

## 3. 可供 grill 选择的认证方案

| 方案 | 核心做法 | 适配程度 | 需要先确认的条件 |
| --- | --- | --- | --- |
| A 手工维护 Cookie CSV | 工程师更新文件；业务 JMX 读取，发固定 Cookie | 最薄；需确认 CSV 与现有预检/路径要求 | 单会话还是多账号；列格式；有效期；EOF 与映射策略 |
| B 独立自动登录准备计划 | 生成独立登录 JMX，短执行后本地固定程序导出 Cookie CSV；业务 JMX 只消费 | 可避开现有业务消费者的 setUp/JSR223 限制；新增认证准备器自身需要验证 | 登录链、成功断言、必需 Cookie、账号绑定、刷新时机、写文件位置 |
| C 每轮每线程首次登录 | 同线程原生 Cookie Manager + 首次登录 + 业务循环 | JMeter 可表达；当前候选需要扩展 | OnceOnly/相关控制器支持、登录采样与目标统计隔离、登录失败处理 |

A、B 都可能满足用户的文件使用习惯；C 更贴近线程内独立浏览器会话。三者不能仅按“更自动化”选择。登录是否有验证码/SSO/CSRF、一次登录是否踢掉旧会话、Cookie 是否频繁续期、会话是否跨并发轮次有效，需用户或接口规范提供依据。

**优先建议：**在保持现有 runner 的前提下先讨论 A/B，首轮 grill 明确 CSV 是否必须作为标准交接物及需要多少独立账号；若用户要求每线程稳定会话，再讨论 C 或 CSV 固定分配扩展。不得默认把所有并发共享一个账号解释为真实独立用户。

## 4. 短试跑的能力与验收边界

官方 CLI 提供 `-n -t -l -j`，`-e -o` 可以在执行后生成报告，报告输出目录需不存在或为空；`-J` 可覆盖 JMeter 属性，但只有脚本使用该属性时才会作用到线程、循环等配置。[Apache JMeter：Getting Started](https://jmeter.apache.org/usermanual/get-started.html)

Dashboard 是采样日志的报告；`sample_filter` 可以过滤用于图表与统计的样本。因此登录/前置和业务请求应该采用独立稳定标签，试跑与后续寻峰都应核对目标 HTTP 请求自身的数据，不能把 Total 当成目标指标。[Apache JMeter：Generating Dashboard](https://jmeter.apache.org/usermanual/generating-dashboard.html)

**建议的分层检查（待确认）：**

1. 只读预检：JMX 能解析，组件在目标 runner 支持范围，CSV/外部文件可定位，变量与引用完整，目标/前置顺序确定，超时/有限预算明确。
2. 经批准的低负载真实试跑：从副本运行，明确并发、循环或时长、每个请求的调用预算；每条目标均应实际出现，认证与业务断言通过，JTL 和日志可读取。
3. 产物核验：确认进程真实退出、采样结束、目标样本存在、失败原因清晰；需要报告时核对官方目标行。退出 0 不单独作为“所有请求正确”的证明。
4. runner 兼容交接：调用消费者的只读预检；记录通过脚本哈希、文件依赖版本/哈希、环境与 JMeter/Java 版本、已确认目标/前置/断言。试跑副本与最终交付脚本的不同项必须可解释。

短试跑证明“本次环境、这些输入与有限执行范围可运行并满足已确认功能条件”，不证明峰值、容量、正式并发下错误率，亦不能永久证明 Cookie 有效。已有 JMX 的试跑若要修改线程数、循环/时长、启用集合或监听器，应先展示精确副本修改集；这与 runner 只改并发/启用状态的原约束属于不同操作契约，需要独立确认。

**建议测试用例族：**cURL GET/JSON POST/表单/重复参数/中文与转义；Header 有效值与正文编码；正常登录/业务 200 失败/重定向登录页/缺 Cookie/多 Set-Cookie；CSV 引号、缺列、空行、EOF、多账号超额；已有 JMX 不支持构件/外部依赖缺失；目标无样本/异常退出/报告不完整；脚本或 Cookie CSV 变化后交接证据失效。所有业务执行留待后续授权；本轮没有执行这些案例。

## 5. 后续问题建议及其依据

| 顺序 | 需要 grill 的决策 | 为什么应先问 |
| --- | --- | --- |
| 1 | cookie.csv 是否为必须的交接物，还是可选择每线程内存会话？ | Cookie Manager 与 CSV 是不同能力，且当前 runner 不支持部分一次登录构件 |
| 2 | 一个会话供全部线程，还是每个线程独立账号/会话？ | 影响 CSV 格式、账号数量、线程绑定与性能结论 |
| 3 | 工程师提供哪些成功依据：状态码、业务码、必须字段、响应样例或接口文档？ | cURL 只含请求，HTTP 默认成功范围不能证明业务成功 |
| 4 | 首期支持哪些 cURL 方法/正文/选项与登录链？ | 原生导入也会忽略或警告；不支持项需要明确处理 |
| 5 | 试跑预算与已有 JMX 可改的副本字段？ | 低负载真实执行仍有实际请求；-J 并不自动改变硬编码配置 |
| 6 | 试跑通过的必要条件与失败后处理？ | 启动成功、目标请求正确、runner 兼容、报告完整是不同结论 |
| 7 | 登录何时刷新，以及多久/何种变更后重做试跑？ | Cookie 过期、脚本/数据/环境变化会使旧通过证据不再适用 |

## 证据质量说明

所有外部引用均为 Apache JMeter、curl 官方或 HTTP Working Group 原始资料；JMeter 实现细节固定到 rel/v5.6.3，不将滚动版手册当成跨版本兼容承诺。本地 runner 限定由同轮兼容代理提供，后续总路由应核对其正式报告。建议、推论和待确认条件均与事实分开；本文件没有定义新 Skill 已实现、已试跑或已经通过验收。
