> 公开投影：业务规则与原编号保留；“本轮”指源文档编写阶段。源哈希、路径适配与当前发布范围见 jmeter/docs/publication-context.md 及导出清单。

# Cookie 是否必需：可判断与不可推断的边界

查证日期：2026-10-13。独立 grill-with-docs 的 matt-research 辅助研究；仅阅读一手标准并复用既有 JMeter 5.6.3 资料。未执行 cURL/JMeter、未访问业务目标、未安装依赖，未修改需求或源码。

## 结论

浏览器 cURL 是否携带 Cookie，以及试跑的 401/403，**都不能单独证明该接口必须通过 Cookie 认证**。writer 可识别请求里已有的认证材料、保留已知行为、提出有依据的缺项；遇到证据不足，应标明不确定，而非把其他认证改成 Cookie。

用户已确认的流程仍成立：提供登录接口与账号时取得 Cookie；未提供时识别是否有 Cookie 使用需求，确有需要则生成待填写 cookie.csv、原生 CSVDataSet 和 Cookie 变量。本研究只澄清“识别需求”的证据，不新增认证方案。

## 一手依据与判断表

RFC 6265 规定 Cookie 的传输、作用域及有效期，但不定义 Cookie 值的业务语义；浏览器会携带适用且未过期的 Cookie。由此不能仅凭 Cookie 名或存在性判断它就是认证凭据。[RFC 6265：4.1.1、4.1.2](https://httpwg.org/specs/rfc6265.html#section-4.1.1)

| 观察到的材料 | 可以得出的结论 | 不能直接得出的结论 |
| --- | --- | --- |
| cURL 含 `Cookie:` 或 `--cookie` | 本条捕获请求发送了这些 Cookie，可据此参数化复现 | 所有 Cookie 都用于认证；去掉一定失败；只有 Cookie 一种认证 |
| cURL 不含 Cookie | 本条请求文本没有显式发送 Cookie | 接口匿名；不需要认证；应该新增 Cookie |
| 返回 Set-Cookie 或登录 JSON 有 cookie 字段 | 服务端提供了某种 Cookie 数据；需要核对目标接口用法 | 目标必须用它认证，或它可以替代原 Authorization |
| 试跑 401 | 该请求缺少有效认证凭据或所给凭据被拒绝，需结合认证挑战与接口规则 | 原因一定是缺 Cookie，或应切换为 Cookie |
| 试跑 403 | 请求被理解但被拒绝；可能所给凭据权限不足，也可能与凭据无关 | 更新 Cookie 就能修复，或需要主动登录重试 |
| 不含 Cookie 的试跑通过业务断言 | 在本次已提供的全部其他条件下请求成功 | 接口普遍无需认证，其他头/参数中的凭据无关紧要 |

RFC 9110 的 401 定义要求服务端提供适用的 WWW-Authenticate 挑战；403 明确允许与凭据无关的拒绝原因，且不建议用相同凭据自动重试。因此状态码应用于定位缺项，而非推定 Cookie 方案。[RFC 9110：401](https://httpwg.org/specs/rfc9110.html#status.401)、[RFC 9110：403](https://httpwg.org/specs/rfc9110.html#status.403)

若实际服务端未提供规范要求的挑战，writer 应记录事实与可见响应证据，不能据“没有 WWW-Authenticate”反推 Cookie 认证。

## 哪些证据更可靠

1. 接口/登录规范明确目标接口需要某个 Cookie，或工程师给出明确的认证与 Cookie 名映射。
2. 原请求与登录响应、后续目标请求能形成对应关系：具体 Cookie 字段如何得到、以哪个名称发送、供哪个目标使用。名称像 session/token 只作线索，不作业务规则。
3. 已授权且受控的成对验证：其他输入相同，携带 Cookie 时满足业务成功条件，移除时得到明确的缺会话/认证错误。此证据只适用于所验证的环境和请求；单纯响应变化可能是个性化、CSRF 或其他 Cookie 依赖，仍不应笼统称为认证证明。

以上第 2、3 项是基于协议语义提出的证据方法，不是本轮已执行结果，也不意味着额外请求得到授权。已有 cURL 携带 Cookie 时，可以为保持捕获请求生成 CSV 引用，准确表述为“复现已有 Cookie 使用”；无需虚构“已证明认证必需”。

## Bearer 等其他认证不能直接换成 Cookie

Bearer 的标准发送方式为 Authorization 头中的 Bearer 方案。RFC 6750 也将 invalid_token 对应 401，将 insufficient_scope 对应 403；这些反例证明 401/403 本身并不专属于 Cookie。[RFC 6750：2.1](https://www.rfc-editor.org/rfc/rfc6750.html#section-2.1)、[RFC 6750：3.1](https://www.rfc-editor.org/rfc/rfc6750.html#section-3.1)

把原 Authorization 值搬成 Cookie、猜一个 Cookie 名、把 Basic 凭据或业务签名替换成 Cookie，会改变请求协议语义。只有目标服务的明确规则支持另一种传递方式时才可以转换。现有其他认证材料应保留，不因这次 Skill 聚焦 Cookie 而静默改写。

## 对下一决策的最小建议

- **已有 Cookie 或明确 Cookie 规范：**按既定 Cookie 生成流程处理；区分“沿用捕获请求”与“已经证明必需”。
- **没有 Cookie、已有其他明确认证：**保留原认证与静态请求内容，不自动加 Cookie。
- **证据不足或试跑 401/403：**报告已知材料和缺项，请工程师补充目标认证依据或 Cookie 使用说明；不将状态码当成自动创建 Cookie 认证的依据。

最需要根代理确认的是：**writer 遇到证据不足时是否先记录不确定并请求必要信息，而非强行二选一判断。**这一边界解决真实性问题，不要求重新询问已确认的登录流程、业务断言或试跑数值。CSV 设置和 JMeter 兼容规则沿用既有研究，本文件不重复扩展。
