> 公开投影：业务规则与原编号保留；“本轮”指源文档编写阶段。源哈希、路径适配与当前发布范围见 jmeter/docs/publication-context.md 及导出清单。

# Writer 编写/验证与 Runner 正式寻峰的解耦边界

日期：2026-10-13。状态：只读研究；未开发、未执行任何 JMeter/业务脚本、未修改原 Runner。本文保留前两份研究作为历史方案，不覆盖它们；前一份 writer executor / wrapper 正式运行方案不再作为当前候选。

## 当前明确范围

- **jmeter-tps-writer**：把 curl 编写为 JMX，处理请求头、断言与认证；按独立接口做 **1线程、业务组配置时长1秒** 的验证；交付脚本及三层验证结论。
- **jmeter-tps-runner**：独立启动正式寻峰；50等正式并发、逐请求/逐轮执行、粗测/细测、质量门槛和报告仍由它负责。
- 保留此前确认：同一 JMX 里 **setUp 认证组 + 业务组**，正式每轮重新准备 Cookie。
- Cookie 来自登录响应 **JSON字段**；对应流程是 JSON 提取 → 固定 CSV 导出构件 → CSVDataSet 读取 → Cookie变量/动态 Header。不是依赖 HTTP Set-Cookie 自动捕获。
- Cookie CSV 的读取和分配使用 JMeter 原生 CSVDataSet；不自研每线程账号/身份调度，不增加 writer 正式寻峰进程。
- 1秒替代此前“1次”的试跑候选。它是业务线程组的配置时长，不是进程硬墙1秒；认证准备、在途请求结束和报告生成可能使总用时更长。不能把1秒解释为只发1个样本。

## 面向用户的结论

**可以保持两个 Skill 独立，不需要新增正式运行时。**writer 只在编写和验证阶段工作；正式 Runner 仍调用官方 JMeter 对完整 JMX 发起每轮运行。

但现有 Runner 的输入资格与隔离逻辑必须做少量必要适配，否则会拒绝 setUp，或把登录 HTTP 禁用。最小范围是 **识别/选择认证前置、保留本轮认证请求、资格验证固定 CSV 导出与生成依赖**。不需要重写寻峰算法，也不需要新造账号分配算法。

## 已有能力与新资格分开

本地依据为指定工作区候选：

`work/jmeter-workbuddy-development-20260921/candidate/jmeter-tps-runner/`

| 构件/行为 | 现有依据 | 需要做什么 |
|---|---|---|
| XML 通用解析 | `scripts/jmx.py:67–105` | 已遍历任意元素/hashTree，不必重造 XML 解析器；需补认证组角色/身份与选择规则。真实 JMX 类名应以5.6.3保存结构核对，不以UI显示名猜测。 |
| 标准 ThreadGroup、HeaderManager、CSVDataSet | `scripts/preflight.py:7–12` | 已在 SAFE，不是本次新增资格原因。writer 负责把其参数和作用域写对。 |
| JSON 提取器 | `scripts/preflight.py:11–13,61–65` | 已支持的实际节点是 **JSONPostProcessor**；提取器/变量依赖仍需正常确认与试跑。不能另造“JSONExtractor”标签并认为现有代码认识。 |
| 常用断言 | `scripts/preflight.py:10–12` | JSONPathAssertion / ResponseAssertion等已有资格；writer按已确认的 success=true 编写对应断言。 |
| 活动 setUp 认证组 | `scripts/jmx.py:58–64,99–103`；`scripts/preflight.py:7–12,59–60` | 目前不识别为支持线程组，也不在 SAFE，需新增限定认证结构资格。 |
| 固定 CSV 导出构件 | `scripts/preflight.py:7–12,53–60` | 活动 JSR223等脚本未资格；必须只支持经过验证的固定模板/构件，不能把所有任意脚本都加入 SAFE。 |
| 跨组认证 HTTP 保留 | `scripts/jmx.py:113–126,171–184,216–219` | 当前普通前置必须同标准组/同 ancestors；没有进入 selected 的所有 HTTP 都被禁用。需明确区分认证阶段前置与普通业务前置。 |
| 本轮生成 Cookie CSV | `scripts/preflight.py:66–83` | 当前文件须启动前存在、相对迁移阻塞、动态文件无法解析。需支持经过验证的生成依赖，不能靠旧 CSV存在证明本轮刷新成功。 |
| 每轮一个官方 JMeter 进程 | `scripts/controller.py:64–88`；`scripts/process.py:40–61` | 可以保留；每轮执行完整 JMX，由 JMeter完成认证阶段与业务阶段，不由 writer在正式运行时调度。 |
| 官方目标行与寻峰 | `scripts/controller.py:97–119`；`scripts/report.py:67–116` | 可保留业务目标 Statistics 与原寻峰逻辑；认证样本不参与目标峰值评分。 |

## 最小 Runner 兼容补丁面（仅设计，不是本轮开发）

### 1. jmx.py：认证前置与精确启用集合

保留“当前业务目标是标准 ThreadGroup HTTP”的要求。为已确认 setUp 认证组增加角色识别/选择，使认证 HTTP 随当前业务请求启用；普通业务前置仍遵守同组同作用域的旧规则。实际运行集合应为：

**本轮所需认证 HTTP + 当前业务 HTTP + 已确认普通业务前置。**

认证组并发和循环沿用 writer 生成并确认的原配置，不随业务并发档位变化；认证 HTTP 不进入寻峰目标列表。独立副本差异校验仍只允许正式目标线程组并发和 HTTP enabled；若最终设计需要额外属性变化，必须明确列出、验证，不能偷偷放宽整份 XML 比较。

### 2. preflight.py：限定结构/导出构件与文件阶段

新增的是 setUp 认证角色与固定 CSV 导出资格，**JSONPostProcessor、CSVDataSet、HeaderManager 本身不需重新实现**。导出构件只能写入任务已确认的目的文件，需绑定 JSON 提取结果与生成产物；其他活动脚本/插件继续拒绝。

对工程师维护的 CSV仍检查启动前有效；对本轮生成的 Cookie CSV检查经过验证的生成者→读取者关系。只有“存在正确的认证构件”才能处理尚不存在的生成文件，不是免除所有 missing-file / dynamic-file / relative-layout 检查。路径布局应在本次确认时固定，不由正式 Runner任意改JMX路径。

### 3. 现有配置与交接说明：声明认证角色，不新增正式入口

现有目标/前置契约要表达认证阶段与普通前置的区别，让 Runner知道哪些登录 HTTP属于准备、哪些业务 HTTP要寻峰。writer交付最终JMX及摘要；Runner对同一最终JMX重新prepare、校验SHA、确认本次正式任务。writer的1秒试跑授权不自动扩展为正式多轮授权。

原 CLI/WorkBuddy桥接仍可以保留为正式入口：**不存在引入 writer executor、复制核心或由 writer编排正式轮次的需要。**变更发生在现有消费者的输入识别和资格规则，而非新运行时。

### 4. 认证失败与报告：保留已有技术故障路径，按最终契约补证据

JMX内必须保证认证/JSON提取/CSV导出失败时不会用旧 Cookie继续发业务压力。这个保证要在固定认证构件和真实试跑中证明，不能仅依赖 CSVDataSet已SAFE或默认success断言存在。脚本处理顺序、旧文件失效和阶段完成需验证。

现有控制器已经把非零退出/目标报告行缺失归为技术问题，并结束当前目标、不自动重发（`controller.py:96–116`）。这可以作为基础，但**是否需要新增明确的认证失败分类或认证产物证据读取，要随最终故障处理契约决定**；不以“已有技术错误”冒充认证阶段已经验收。Q9尚未选择，本文不替用户补失败策略。

原 report.py的目标标签/P90/TPS读取无需为了JSON Cookie重写；加入认证后，官方报告General Infos仍按完整本轮JMeter执行读取，不能把时间人工改成另一个窗口。

## “JMeter自行分配”仍需要 writer 编写配置

原生CSVDataSet负责实际读取和分配，因此无需自研每线程账号选择函数。writer仍需配置：Cookie列名、CSV格式/编码/表头、Sharing mode、Recycle on EOF、Stop thread on EOF，以及Cookie变量引用和作用域。

配置决定“单会话被多线程共享”或“多行账号/Cookie按原生CSV行为分配”；**使用原生组件不意味着这些参数可以省略**。也不自行追加“每个线程必须固定绑定唯一账号”等用户未提出的限制。共享HeaderManager只负责动态Cookie等更新值；各curl静态头按其真实语义保留。

## 关联验证边界

以下全部是未来计划，本次未运行：

1. 原无认证/普通同组前置兼容不回退，HTTP启用集合与源SHA/副本白名单仍成立。
2. setUp登录 → JSONPostProcessor → 固定CSV导出 → CSVDataSet → Cookie Header的合成验证；登录返回success=false、Cookie缺失、CSV写失败时不发依赖业务请求，也不回退旧文件。
3. 会话共享和多账号均使用原生CSV配置验证；检查EOF、空值及作用域，避免额外身份算法。
4. writer独立1线程、业务组配置1秒验证；记录实际样本和总用时，不虚称硬墙1秒或只有1次请求。
5. 经授权后，Runner真实每轮一个进程执行同一JMX，认证HTTP不被隔离逻辑关掉、其他业务HTTP不重叠、目标官方统计行唯一且正确。
6. 针对认证阶段改动补实际问题/停止证据；不因核心算法未改就继承新进程内结构的资格，也不要求重跑无关历史实验。

## 与旧研究的关系

- `research-runner-compatibility.md`：解释现有消费者为何直接阻塞 setUp/CSV写入；结论仍适用。
- `research-writer-adapter-boundary.md`：此前研究的“两进程 writer executor”路径；已因用户拒绝writer参与正式寻峰而退出当前方案。
- 本文：**writer编写与短试跑 → Runner独立正式寻峰**，只研究必要消费者兼容修订。未批准或执行任何开发与发压。
