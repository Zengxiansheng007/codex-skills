> 公开投影：业务规则与原编号保留；“本轮”指源文档编写阶段。源哈希、路径适配与当前发布范围见 jmeter/docs/publication-context.md 及导出清单。

# 线程组默认 HTTP 请求头：JMeter 5.6.3 窄研究

查证日期：2026-10-13。研究代理采用 matt-research；只查资料与读取本地预检代码，不运行 JMeter、不生成业务 JMX、不修改 runner、不安装依赖。

输入约定：WorkBuddy / Windows / JMeter 5.6.3；同 JMX 的 setUp 认证与普通业务组；两种会话模型均支持；默认响应业务断言 success=true；试跑为副本 1 线程 / 1 次，有限字段修改；首期正文范围为 query、JSON、URL 编码表单和文本。本文件解释用户所说的“线程默认 HTTP 请求头”，不把以下候选模板自动视为已确认要求。

## 1. 能力与作用域

JMeter 的“默认请求头”可通过挂在 Thread Group 内的 HTTP Header Manager 实现，对该组作用域内的 HTTP 请求生效。官方高级 Web 计划建议通常挂在线程组级，有请求差异时可以分别配置请求对象。[Apache：Using a Header Manager](https://jmeter.apache.org/usermanual/build-adv-web-test-plan.html#header_manager)

这是一份线程组下请求共同使用的配置，不表示给某个运行线程创建独立 GUI 组件。setUp 认证组与业务组可分别放置各自默认头，不宜把业务认证 Cookie 全部放到 TestPlan 根上，导致登录请求也继承尚未准备的状态。

## 2. 子级覆盖组级：固定 5.6.3 的完整源码链

1. `TestCompiler.saveSamplerConfigs()` 从当前 sampler 所在近层向祖先远层收集配置；`configureWithConfigElements()` 按列表顺序将配置加到 sampler。[TestCompiler.java：L192–200、L286–299](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/core/src/main/java/org/apache/jmeter/threads/TestCompiler.java#L192)
2. `HTTPSamplerBase.setHeaderManager()` 将已加入的 Header Manager 与随后加入的管理器合并。[HTTPSamplerBase.java：L873–885](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/protocol/http/src/main/java/org/apache/jmeter/protocol/http/sampler/HTTPSamplerBase.java#L873)
3. `HeaderManager.merge()` 按不区分大小写的头名判断重复，重复时保留已有项，仅加入缺失的头。[HeaderManager.java：L269–293](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/protocol/http/src/main/java/org/apache/jmeter/protocol/http/control/HeaderManager.java#L269)

**结论：**在标准树结构内，“请求子级 Header Manager 的同名值优先于 Thread Group 默认值”有 5.6.3 源码依据。因此可采用 Common 头 + 请求 override。不建议在同一层放多个相互冲突的管理器或重复同名项，让结果依赖同层遍历顺序；生成阶段应给出每个请求最终有效头表。

例：组级 `Accept: application/json`，某请求子级有原 cURL 的 `Accept: application/json, text/plain, */*`，该请求沿用子级值；另一个没有子级 Accept 的请求继承组级值。子级空值是配置空值，不应被解释成可靠的“删除上级字段”操作。

## 3. 分清返回类型、发送类型与传输配置

Accept 表示希望接收的媒体类型，Content-Type 表示当前请求正文的媒体类型；两者不是同一个默认开关。HTTP 规范允许内容协商，Accept 本身不能保证服务端业务成功。[HTTP Working Group：RFC 9110](https://httpwg.org/specs/rfc9110.html#field.accept)

5.6.3 HttpClient4 的实现先依据 sampler KeepAlive 设置 Connection，再添加 Header Manager；若管理器也写 Connection，可能产生冲突或重复。Cookie Manager 在普通头之后处理 Cookie，存在适用 Cookie 时使用 setHeader 覆盖该请求 Cookie；Content-Length 的手工覆盖被拒绝。POST 正文缺 Content-Type 时还可能采用表单类型，而不是自动识别 JSON。[HTTPHC4Impl.java：L1221–1228、L1292–1298、L1321–1338、L1508–1566](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/protocol/http/src/main/java/org/apache/jmeter/protocol/http/sampler/HTTPHC4Impl.java#L1221)

## 4. 推荐候选模板

这是一套适合已确认 JSON success 响应约定的建议；Accept 默认值是本项目选择，不是 JMeter 官方要求所有请求强制采用的值。原 cURL 已明确给出的兼容头优先保留在请求层，删除或改变有语义的头需要有依据。

| 层级 | 候选配置 | 说明 |
| --- | --- | --- |
| 业务 Thread Group 默认 Header Manager | `Accept: application/json` | 适合本项目默认 JSON 业务断言；原 cURL 的明确 Accept 可在请求层覆盖 |
| 业务组共同认证头 | CSV 模式需要时 `Cookie: ${cookie_header}`；或接口需要的 `${authorization}` | 按已选择的认证来源启用，避免固定真实值；不同域名/不同认证请求放到请求层 |
| 业务组共同业务头 | 仅保留该组全部请求确实需要的租户/版本等业务字段 | 不能凭经验统一伪造 |
| JSON 请求子级 Header Manager | `Content-Type: application/json` | 正文编码独立保持与原请求/接口约定一致 |
| URL 编码表单请求子级 | `Content-Type: application/x-www-form-urlencoded` | 表单参数以对应形式构造，不能继承 JSON 发送类型 |
| 文本请求子级 | 沿用原 cURL 的明确类型，常见为 `text/plain` | 不将 XML 等其他文本类型无条件改为 text/plain；缺类型时明确标出待处理项 |
| 无正文 query 请求 | 不默认增加 Content-Type | 查询参数与响应 JSON 并不要求请求正文类型为 JSON |
| HTTP Request / Defaults 的传输设置 | 候选 `Use KeepAlive=true`；Header Manager 不另写 Connection | KeepAlive 属请求连接策略；显式原请求差异需要单列处理 |
| User-Agent、Origin、Referer、浏览器提示头 | 不生成统一假浏览器值；保留原请求必要字段 | 是否需要由原请求与业务行为决定；未提供时不擅自伪造 |
| Content-Length、普通 Host | 不固化 Content-Length；Host 通常依据 URL | 显式虚拟主机/路由测试 Host 仍需要保留特殊处理 |

**结构示意（不是已生成 JMX）：**

```text
TestPlan
├─ setUp 认证组
│  ├─ 认证组自己的 Header Manager
│  └─ 登录请求及 Cookie 准备
└─ 业务 Thread Group
   ├─ 默认 Header Manager：Accept + 该组共同认证/业务头
   ├─ JSON 请求 → 子级 Content-Type=application/json
   ├─ 表单请求 → 子级 Content-Type=application/x-www-form-urlencoded
   └─ 文本请求 → 子级原请求的文本 Content-Type
```

不在混合正文的组级默认中统一放 Content-Type=application/json，可以减少逐请求漏覆盖后把表单或文本错误发送为 JSON 的风险。共同响应类型与不同发送正文类型可以同时存在。

## 5. Cookie 来源必须唯一而可解释

“CSV 固定 Cookie 请求头”和“Cookie Manager 动态维护 Cookie”是两条不同发送路径。前者按 CSV/账号映射构造 `${cookie_header}`；后者由 Cookie Manager 按 URL 选取 Cookie。若两者同时对同一请求负责，普通头中的 CSV Cookie 可能被管理器覆盖，不能简单称为“自动合并”。依据见上面的 HTTPHC4Impl 调用链。

首期设计应为每个请求明确 Cookie 的唯一权威来源；登录准备阶段可以使用 Cookie Manager 解析响应，再导出供业务组消费的 CSV。业务消费阶段是否继续接收/维护服务端续期 Cookie，属于会话契约，需要在认证方案中说明，不能在默认头模板里隐式决定。

## 6. 本次是否需要修改 runner

读取当前候选 `scripts/preflight.py` 后核实：SAFE 已含 HeaderManager（第 8 行），未知激活构件检查位于第 59 行。因此“增加线程组默认 HTTP 请求头”本身不要求扩展 runner 构件支持。本地 preflight.py（历史本地参考，未随本次导出）

同 JMX setUp 认证、CSV 生成/账号映射以及每轮准备的执行契约仍需要已纳入设计的 runner 适配；这些修改的依据是认证与准备组结构，而不是 Header Manager。设计需要确保后续寻峰仅变更业务组并发，不顺带改登录准备规模，并且继续使用目标 HTTP 请求自身统计。此处仅记录关联范围，没有实施任何修改。

## 7. 后续针对性验证依据

- 组级头继承到请求；请求子级同名头覆盖组级；头名大小写差异不产生意外重复。
- 同一组 JSON、表单、文本、query 请求的最终 Content-Type/正文形式分别符合输入。
- KeepAlive 选项与实际 Connection 不冲突。
- CSV Cookie 与 Cookie Manager 模式分别验证，来源冲突时给出明确结果而非静默混用。
- 认证组不会继承业务组未就绪的 Cookie；业务组不会错用旧登录状态。
- 准备与业务采样标签隔离；正式 runner 的并发变化只作用于已确认业务组。

本轮没有执行以上案例；结论区分官方事实、源码推论与候选模板。
