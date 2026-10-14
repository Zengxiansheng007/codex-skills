> 公开投影：业务规则与原编号保留；“本轮”指源文档编写阶段。源哈希、路径适配与当前发布范围见 jmeter/docs/publication-context.md 及导出清单。

# JSON Cookie 与 1 线程 / 1 秒试跑：窄研究

查证日期：2026-10-13。仅检索 Apache 官方手册、固定 rel/v5.6.3 源码并读取现有预检白名单；未运行 JMeter、未开发或修改源码、未接触真实 Cookie。新 Skill 为 jmeter-tps-writer。

## 本轮已确认方向

- writer 负责写脚本与执行验证，不参与正式每轮 runtime。
- 试跑改为 **1 线程 / 1 秒**，取代之前的 1 线程 / 1 次；不重新询问已确定数值。
- Cookie 从登录响应 JSON 提取，再写 CSV、配置变量；采用 JMeter 原生 CSV 分配，不自研固定身份算法。
- 共享默认头只放 Cookie 等更新内容，静态头保留 cURL；响应业务断言仍为已确认的 success=true。
- 已有“同一 JMX 的 setUp 认证组 + 业务组”没有因本次缩减 writer 职责而自动撤销。

## 1. 原生 duration=1 秒不等于整个进程 1 秒硬截止

5.6.3 `ThreadGroup.scheduleThread()` 将开始时刻加 duration 秒设置为线程结束时刻；`JMeterThread.processSampler()` 在执行 sample package 后检查 scheduler。官方手册明确结束条件在样本之间检查，不打断等待响应的采样器。[ThreadGroup.java：L186–203](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/core/src/main/java/org/apache/jmeter/threads/ThreadGroup.java#L186)、[JMeterThread.java：L467–475](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/core/src/main/java/org/apache/jmeter/threads/JMeterThread.java#L467)、[官方 Thread Group 说明](https://jmeter.apache.org/usermanual/component_reference.html#Thread_Group)

**可核实的例子：**业务线程组设 duration=1，首个请求等待 1.5 秒才返回；原生 scheduler 会让这个正在执行的请求完成，再决定停止，不在第 1 秒强杀它。总墙钟还包括 JMeter/JVM 启动、setUp 登录、线程组启动/延迟与报告生成；ramp/timer 设置会影响可用采样窗口，不能把这些统称为固定额外秒数。1 线程的第一个线程通常立即启动，不应声称其 ramp-up 必然额外等待完整 ramp 秒数。

若多个目标在一个业务组串行执行，第一个慢请求可能耗完窗口，后续目标没有实际样本。1 秒也不代表只调用一次：快速接口可能在循环中执行多次；循环、timer、调度延迟决定实际数量。

**试跑判定边界：**目标无样本、只登录未执行业务、CSV 未完成或关键目标未覆盖，应如实报告未验证/失败原因，不能因启动成功或退出 0 报通过。1 秒不是容量或并发性能验证。

**唯一优先澄清的时长语义：**该 1 秒是“业务线程组 scheduler 的采样窗口，认证和已发出的请求完成另计”，还是“整个过程含认证在 1 秒强制结束”？前者直接对应原生 JMeter duration；后者需要中断语义，不能用 duration=1 假装实现。本问题确认含义，不重问数值，也不默认追加时长。

## 2. 登录 JSON 提取可用原生构件，写 CSV 仍是另一件事

JSONPostProcessor 从响应正文按 JSONPath 提取，写入当前线程变量；未提取到或异常时可能使用默认值。它本身不是 CSV 写入器，也不会因写入默认值自动使样本失败。JSONPathAssertion 可对正文路径及期望值断言，缺路径/解析异常会失败。[JSONPostProcessor.java](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/components/src/main/java/org/apache/jmeter/extractor/json/jsonpath/JSONPostProcessor.java#L60)、[JSONPathAssertion.java](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/components/src/main/java/org/apache/jmeter/assertions/JSONPathAssertion.java#L107)

本地候选 `preflight.py` 的 SAFE 已含 JSONPostProcessor、JSONPathAssertion 和 CSVDataSet；JSONPostProcessor 同时在 EXTRACTORS 中。它们属于既有支持范围，但不能因此声称 setUp 或 CSV 导出构件已经支持。本地 preflight.py：L7–13（历史本地参考，未随本次导出）

**生成需要的真实输入：**登录响应样例/规范、JSON 字段路径、值的含义，以及该值应对应 cURL 中哪个 Cookie 名。AI 可以根据材料提出映射，但不能自行把任意 token 字段解释为某个 Cookie。无需重新确认已确定的业务 success=true。

| 登录响应提供什么 | 提取与发送的区别 |
| --- | --- |
| 完整头值，例如 `SESSION=abc; CSRF=xyz` | 可提取为 cookie_header，由业务头引用；仍需核对允许目标与完整性 |
| 只有会话值，例如 `abc` | 还需明确 Cookie 名，例如 cURL 已有的 SESSION；发送为 `SESSION=${session_value}` |
| 多个字段分别表示多枚 Cookie | 各字段与 Cookie 名建立映射，再按 Cookie 头语义组合，不能只拿其中第一项 |

HTTP Cookie 请求头由名称和值组成；JSON 中的裸值不自动携带 Cookie 名称。[HTTP Cookie 规范](https://httpwg.org/specs/rfc6265.html#section-4.2)

CSV 导出仅需实现已明确字段的有限落盘步骤，不引入正式每轮 writer 包装器或自研身份调度。应核对提取结果有效、输出完成和变量引用；提取到空值/缺失默认标记不能继续伪造登录成功。具体文件写入构件及同 JMX 运行兼容仍需在设计中明确，不能把原生提取器说成已提供持久化。

## 3. 使用原生 CSV 分配，要准确描述其效果

CSVDataSet 在每次主迭代开始取下一行并设置当前线程变量。默认共享全线程读取游标；模式可改为当前线程组、当前线程或标识键。EOF 时回卷、停止线程或写入 EOF 标记由对应选项决定。[CSVDataSet.java：L42–64、L150–225](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/components/src/main/java/org/apache/jmeter/config/CSVDataSet.java#L42)

因此“原生 CSV 分配”不应被表述为每线程永久固定账号；共享游标也不是 Cookie Manager 的独立会话。不同迭代是否换到新行，应与配置一起交付。

实际设置仍待本方案选择：

| 项 | 原生行为/待定点 |
| --- | --- |
| Sharing Mode | 默认 All threads；默认事实不是用户已确认配置 |
| Recycle on EOF | 决定是否回到文件开头 |
| Stop thread on EOF | 不回卷且到 EOF 时是否停止线程 |
| 文件列、编码、引号 | 必须与 Cookie CSV 产物一致 |
| 账号数量不足 | 按原生 EOF 策略明确说明，不暗中自研分配或保证固定身份 |

本轮不替用户决定上述设置，也不把多账号固定绑定作为隐含要求恢复。

## 4. 仍需处理的真实架构冲突

writer 退出正式 runtime 后，之前“每档由 writer 包装认证再调用业务”的候选路线已不属于本次 writer 范围。可是同 JMX setUp + 业务仍是已有要求，现有 runner 又会拒绝其未支持的激活构件；不能简单宣称原生 JMeter 支持就完成交接。

需要一次明确的产品设计决定：正式消费端如何支持作者 JMX 的 setUp 认证与 CSV 落盘。可以设计必要 runner 适配，但不应擅自撤销同 JMX 结构、重新让 writer 管每轮或把 Cookie JSON 提取当成全部适配完成。有关已有兼容证据见 [research-runner-compatibility.md](research-runner-compatibility.md)，关于原生 setup 时序见 [research-same-jmx-threadgroups.md](research-same-jmx-threadgroups.md)。

## 供根代理使用的必要问题顺序

1. 只澄清“1 秒”的作用范围与结束方式，不重问 1 线程或 1 秒数值。也要据此说明多请求可能未覆盖的结果，不自行加长验证。
2. 在具体任务中拿到登录 JSON Cookie 路径及 Cookie 名映射；已给足材料时直接采用，不重复问业务断言。
3. 确定原生 CSV 设置及其自然分配效果，不再讨论自研固定身份算法。
4. 确定保留同 JMX 认证结构时正式 runner 的必要兼容范围；writer 职责停在脚本生成与执行验证。

所有执行效果尚未实测；本文件没有宣称 1 秒试跑、JSON 登录或 CSV 导出已通过。
