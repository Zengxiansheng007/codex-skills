> 公开投影：业务规则与原编号保留；“本轮”指源文档编写阶段。源哈希、路径适配与当前发布范围见 jmeter/docs/publication-context.md 及导出清单。

# 同一 JMX 分登录与业务线程组：JMeter 5.6.3 证据补充

查证日期：2026-10-13。范围为 Apache 官方手册与固定 rel/v5.6.3 源码；未执行 JMX、未安装依赖、未接触业务账号/Cookie，也未修改 runner。由 matt-research 工作代理完成，未派生代理。

## 本轮输入与结论

用户希望同一 JMX 的不同线程组分别放登录与业务；已确认默认业务断言为响应 `success=true`，单会话共享与多账户独立会话两种模型都要支持。业务断言不再作为待询问事项。本文件补充技术事实，不把这些新结构自动视为现有 runner 已兼容或已获改动授权。

**原生 JMeter 5.6.3 可以在一个 JMX 中使用 setUp Thread Group 登录、再让普通 Thread Group 执行业务。**但 Cookie 不会因放在同一 JMX 而自然跨线程组共享；CSV 导出、读取及账号绑定仍需明确设计。“登录准备每次执行一次”和“整个寻峰任务只登录一次”也不是同一个结论。

## 1. 顺序保证：应使用 setUp，而非仅把普通登录组排在上面

官方手册将 setUp Thread Group 定义为普通线程组之前的准备动作。[Apache：setUp Thread Group](https://jmeter.apache.org/usermanual/component_reference.html#setUp_Thread_Group)

5.6.3 `StandardJMeterEngine.run()` 先启动所有 setup 组，在所有 setup 线程退出后才进入普通组启动循环。普通组的启动后等待仅在 serialized 为真时发生；多个 setup 组之间也只有串行模式才逐组等待，否则可以互相并行，但普通业务组仍等待全部 setup 结束。[StandardJMeterEngine.java：L422–480](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/core/src/main/java/org/apache/jmeter/engine/StandardJMeterEngine.java#L422)

**事实边界：**线程组退出表示执行结束，不自动证明登录成功。登录失败但配置为 Continue 的情况仍可能进入业务阶段；需要在脚本设计中明确准备失败的处理与 Cookie 产物完整条件。

普通登录组 + 普通业务组若未启用串行模式，不能依赖树中上下顺序保证登录已经完成。TestPlan 的序列化配置通过 `TestPlan.serialize_threadgroups` 控制；5.6.3 schema 与 `isSerialized()` 均有对应定义。[TestPlanSchema.kt](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/core/src/main/kotlin/org/apache/jmeter/testelement/TestPlanSchema.kt#L35)、[TestPlan.java](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/core/src/main/java/org/apache/jmeter/testelement/TestPlan.java#L180)

## 2. 同一文件不是同一会话：Cookie 与变量不能直接跨组

Cookie Manager 的初始状态为线程实例提供 Cookie 列表；运行收到的 Cookie 与对应变量在当前线程上下文内维护。静态 Cookie 的保存接口与运行 Cookie 导出不同。[CookieManager.java](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/protocol/http/src/main/java/org/apache/jmeter/protocol/http/control/CookieManager.java#L107)

官方最佳实践明确：变量属于线程，一个线程写入的变量不能被另一线程直接读取；跨组可使用 JMeter 全局属性或写文件后读取。属性全局共享也不等于已实现多账号映射。[Apache：Sharing variables between threads and thread groups](https://jmeter.apache.org/usermanual/best-practices.html#sharing_variables)

**推论：**把 HTTP Cookie Manager 放到 TestPlan 层也不能让 setup 登录得到的运行 Cookie 自动进入每个业务线程；需要明确的数据传递契约。单 Cookie 全局共享可对应“所有并发共用一个会话”；多账户独立会话需要保持账号键与会话、业务线程之间的映射。

## 3. setup 生成 CSV 后业务组读取：原生初始化时序支持，但有前提

5.6.3 `CSVDataSet.iterationStart()` 在内部 vars 尚未初始化时才调用 `initVars()`，后者为 CSV 调用 `FileServer.reserveFile()`；即业务组首次迭代才初始化其读取资源。[CSVDataSet.java：L150–205](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/components/src/main/java/org/apache/jmeter/config/CSVDataSet.java#L150)

FileServer 保留文件路径/别名；有表头时 reserve 会读取表头，没有表头时首次 readLine 创建 Reader。已经存在的相同别名可复用条目及打开的 Reader，不会自动保证覆盖文件后刷新内容。[FileServer.java：L236–265、L314–334](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/core/src/main/java/org/apache/jmeter/services/FileServer.java#L236)

**有依据的可行性推论：**将 CSV Data Set 限定在普通业务线程组内，且没有其他构件提前读取同一输出路径/别名时，setup 先完成 CSV 的写入、关闭与发布，业务组第一次迭代再读取，这条链在原生 5.6.3 时序上可行。本轮只核源码，未做运行验收。

CSV 导出仍需设计这些边界：

- 写入方如何从登录响应收集完整适用 Cookie，以及以账号键组织结果。
- 单共享会话与多账户固定绑定的文件格式、选行及重复策略。
- 输出要在 setup 结束前完整关闭；不让业务组读取半文件。
- CSV Data Set 的作用域仅在消费方，避免登录阶段提前读不存在的输出。
- 输入账号 CSV 与输出 Cookie CSV 使用不同路径/别名，避免共享读取缓存/游标。
- 准备失败时如何防止继续用上一轮遗留的 Cookie 文件。

这些是待形成的实现契约，不能用“添加一个 CSV Data Set”替代。Cookie Manager 的保存功能也不能自动生成需求中的 cookie.csv。

## 4. 登录的次数：每次 JMeter 执行与整个寻峰任务不同

StandardJMeterEngine 的每次 `run()` 都执行 setup 阶段；其时序没有“此前另一个进程已登录，本次跳过”的跨进程逻辑。[StandardJMeterEngine.java](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/core/src/main/java/org/apache/jmeter/engine/StandardJMeterEngine.java#L422)

**推论：**若 runner 每一压测轮都创建新的 JMeter 执行，同一 JMX 中激活的 setup 会在每轮执行，而非整个寻峰任务只执行一次。setup 内登录样本的次数还取决于该组线程数、循环及账号分配：一个线程一次登录与多账号批量准备不能统称为“登录一次”。若产品要求整任务复用已有 CSV，须另外定义缓存/刷新条件，并在 runner 调用边界协调，不能归功于 setUp 本身。

## 5. 默认响应 success=true 的原生断言配置

确认语义为 HTTP 响应 JSON 的根字段 `success`，不是 JTL 的 `success` 列或 `SampleResult.isSuccessful()`。5.6.3 JSONPathAssertion 从响应正文按 JSONPath 取值，按配置比较期望值；缺路径/解析异常会将断言判为失败。[JSONPathAssertion.java：L107–185](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/components/src/main/java/org/apache/jmeter/assertions/JSONPathAssertion.java#L107)

| 配置 | 值 |
| --- | --- |
| JSON_PATH | `$.success` |
| JSONVALIDATION | `true` |
| EXPECTED_VALUE | `true` |
| ISREGEX | `false` |
| EXPECT_NULL | `false` |
| INVERT | `false` |

在非正则模式下，源码解析期望值为 JSON 值后比较，因此响应布尔 true 可通过，false、null、缺字段、字符串 `"true"` 不满足该比较。需要注意它还存在数组元素匹配逻辑：若字段意外为 `[true]`，该断言可因元素匹配通过。因此这组配置是确认业务规则的默认实现依据，不能额外宣称已保证字段一定是标量布尔；若要求严格类型需补约束。以上结果来自源码判断，本轮未运行断言案例。[JSONPathAssertion.java：L119–166](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/components/src/main/java/org/apache/jmeter/assertions/JSONPathAssertion.java#L119)

## 6. 与当前 runner 的交接边界

同轮已有本地兼容研究指出当前候选 SAFE 不含 setUpThreadGroup、OnceOnlyController、JSR223，未知激活构件会被阻断；前置关系限定标准同线程组/同祖先且在目标之前。参见 [research-runner-compatibility.md](research-runner-compatibility.md)。本文件不重复源代码审查，也未更改此限定。

因此，“原生 JMeter 支持一个 JMX 两类线程组”是已核技术事实；“现有 jmeter-tps-runner 已支持它”目前不成立。若选择同一 JMX 的 setup → CSV → 业务结构，后续需要明确扩展消费者的构件范围、准备组识别/启用、并发修改作用域、认证样本与业务样本区分、CSV 导出/绑定及失败处理，再做针对性验收。此研究本身不授权改动 runner。

## 待执行验证（只列依据，不宣称通过）

1. setup 结束事件先于业务首次采样；未生成 Cookie CSV 时业务不误用旧文件。
2. 输出文件启动前不存在，setup 完整生成后业务 CSV 首次读入成功。
3. 共享会话与多账号模式分别核对实际请求中的 Cookie 和线程映射。
4. 多轮独立 JMeter 执行核对每轮 setup 次数与产品约定一致。
5. JSON true、false、字符串 true、缺字段、null、数组等响应验证默认断言及类型边界。
6. 当前消费者先明确兼容扩展，再验证业务组并发调整不会改变登录准备规模，登录样本不会成为寻峰目标。

没有实际测试证据的部分保留为待验证，不以文档检查或源码推论代替运行通过。
