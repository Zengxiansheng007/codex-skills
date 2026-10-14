> 公开投影：业务规则与原编号保留；“本轮”指源文档编写阶段。源哈希、路径适配与当前发布范围见 jmeter/docs/publication-context.md 及导出清单。

# JMeter 5.6.3：目录准备与独立报告步骤的事实核对

日期：2026-10-13。执行方式：matt-research 顺序执行，一手资料检索与本地候选只读核对。未运行 JMeter，也未复现用户所述报告长时间未完成。本文是实际研究证据，不是新增正式需求。

## 已核实事实

1. JMeter 官方支持从已有 CSV 样本日志单独生成 Dashboard：`jmeter -g <log file> -o <output folder>`；另一种方式为采样命令附带 `-e -o`。依据：[5.6.3 固定版本手册](https://raw.githubusercontent.com/apache/jmeter/rel/v5.6.3/xdocs/usermanual/generating-dashboard.xml)，572–586 行；[官网手册](https://jmeter.apache.org/usermanual/generating-dashboard.html#report)。命令仅作方案依据，本轮没有执行。
2. 报告以保存的 CSV 样本字段为输入，必需字段、时间格式及相关报告配置应保持一致；报告输出目录需要为空。依据：上述固定版本手册 85–109、595–603 行；本机 `apache-jmeter-5.6.3/printable_docs/usermanual/generating-dashboard.html` 同时查到对应说明。扩展名为 .jtl 不等于内容必然为合格 CSV。
3. `generate_report_ui.generation_timeout` 出现在 GUI 报告对话框章节；不能直接把它当成 runner 的 CLI 报告超时控制。依据：上述固定版本手册 590–603 行。
4. 报告会处理错误分类；5.6.3 的 `ErrorsSummaryConsumer.getErrorKey` 使用响应码、响应消息，以及符合条件的断言失败消息构造分类键。依据：[官方固定版本源码](https://raw.githubusercontent.com/apache/jmeter/rel/v5.6.3/src/core/src/main/java/org/apache/jmeter/report/processor/ErrorsSummaryConsumer.java)，83–102 行。手册也明确百分位窗口越大占用内存越多，但这不能证明本次卡住由内存导致。

## 当前工作区候选事实

核对的是 `candidate/jmeter-tps-runner`，不是用户正在使用的 WorkBuddy 安装版本。

- `scripts/storage.py` 的 `Store.paths` 按请求名加稳定身份后缀／并发数创建 report、result、plans；报告路径为 report/run-NNN，JTL、日志、控制台及副本带轮次名。目录在每轮选出并发后创建，尚无独立前置入口。
- `scripts/process.py` 的 `run_jmeter` 一条命令同时包含 `-n -t -l -e -o -j`，之后 `child.wait()` 等真实进程退出；未单列 CLI 报告生成的等待上限。
- `scripts/controller.py` 等上述合并执行结束，再调用 `read_report` 获取官方指标和决定后续并发。缺 report 时按目标技术问题结束当前请求，后续请求继续；不能把未生成报告等同于质量超标或零 TPS。
- 当前 writer 规格 `specification-v0.1/change-scope.md` 原建议保留 runner 的 process/storage；用户本次新增需求涉及它们，必须在收尾与后续规格阶段重新核对这些保留范围。访谈阶段不改既有规格或产品代码。

## 推断与待核事项

- 拆分采样和生成步骤可以分别记录真实退出、耗时、日志和失败，保留已完成的 JTL；不能据此承诺报告变快或卡死根因已修复。
- 用户观察到 500 并发、高错误率、十多分钟报告未完成，是现象证据。需要该次 JTL 格式／大小／样本规模、错误消息分类情况、报告日志和进程状态，才能继续判断长计算、资源压力、异常退出、残留进程或其他原因。当前根因未知。
- 若继续以官方 report 为指标权威，报告没有核验通过的轮次不能替换成自算 JTL 指标参与峰值和后续并发计算。如何结束等待、保留候选和推进后续请求，属于本次访谈的用户决定。
- 需要确保未来强制准备步骤与“报告输出空目录”、不覆盖既有轮次、动态细测并发和真实执行证据一致。空目录不能当作某轮已经执行的证据。

## 检索限制

初次查找假定的本地 docs/usermanual 文件路径不存在，改为文件清单核对后找到 printable_docs；未下载依赖。初次尝试官方仓库 v5.6.3 路径返回 404，已改用实际 `rel/v5.6.3` 路径。最终采用的固定版本来源均成功读取；不存在根据失败页面得出的结论。

## 2026-10-13 补充：能否用 result/JTL 获取寻峰指标

问题来源：用户要求先分析 result 统计是否可行，TPS 等是否能直接读取，还是需要再次计算。当前仍未选择改变指标来源。

### 原始字段与直接读取边界

普通 CSV JTL 是逐样本结果，包含可配置的 timeStamp、elapsed、label、success、responseCode 等字段，不含每目标已聚合好的 TPS/P90/错误率。`-l` 的输出内容由保存配置决定，.jtl 扩展名本身不能保证 CSV 格式或所需字段完整。依据：[官方 Listener 手册](https://jmeter.apache.org/usermanual/listeners.html#csvlogformat)，默认保存配置、CLI -l 和 CSV 字段章节；[5.6.3 Sample 源码](https://raw.githubusercontent.com/apache/jmeter/rel/v5.6.3/src/core/src/main/java/org/apache/jmeter/report/core/Sample.java)，141–150、168–188、212–250 行。

不能仅数行得到所有指标：样本数须按当前目标 label 筛选后计数；错误率须累计该目标 success=false；TPS 还需要实际样本时间跨度；P90 还需要 elapsed 分布。success 是 JMeter 的样本成功判定，应包含已配置断言造成的失败，不用 HTTP 状态码单独替代。

### 已核对的官方计算口径

1. `StatisticsSummaryConsumer` 按 sample.getName() 分组，对普通有效目标样本增加总数，success=false 增加错误数；elapsed 无论成功或失败都进入响应时间统计；错误率为错误数×100／总数。依据：[5.6.3 StatisticsSummaryConsumer](https://raw.githubusercontent.com/apache/jmeter/rel/v5.6.3/src/core/src/main/java/org/apache/jmeter/report/processor/StatisticsSummaryConsumer.java)，66–87、125–143、155–157 行。不能把只有成功请求的 TPS 当成当前 Dashboard Transactions/s。
2. TPS = 目标总样本数×1000／（目标最后结束毫秒−目标最早开始毫秒），成功和失败都计入样本数。不能直接除以配置的 120 秒／180 秒。依据：[5.6.3 StatisticsSummaryData](https://raw.githubusercontent.com/apache/jmeter/rel/v5.6.3/src/core/src/main/java/org/apache/jmeter/report/processor/StatisticsSummaryData.java)，39–40、58–59、76–77、215–216 行。时间戳是开始还是结束取决于 sampleresult.timestamp.start，按实际保存配置解释；Sample.getStartTime/getEndTime 已体现两种转换。
3. Dashboard P90 由 `PercentileAggregator(90)` 计算；其窗口来自 jmeter.reportgenerator.statistic_window，源码默认 20000，使用 Commons Math DescriptiveStatistics。依据：[5.6.3 PercentileAggregator](https://raw.githubusercontent.com/apache/jmeter/rel/v5.6.3/src/core/src/main/java/org/apache/jmeter/report/processor/PercentileAggregator.java)，26–43、66–78 行。窗口按每标签实际读入顺序更新；不能未经确认换成全量 JTL 最近排名法，也不能把 Latency 或平均值当 elapsed 的 P90。
4. 百分位估计类型来自 backend_metrics_percentile_estimator，源码默认 LEGACY；可改变，必须核对任务实际生效配置。依据：[5.6.3 DescriptiveStatisticsFactory](https://raw.githubusercontent.com/apache/jmeter/rel/v5.6.3/src/core/src/main/java/org/apache/jmeter/report/processor/DescriptiveStatisticsFactory.java)，23–25、34–36 行。官方手册也说明 Dashboard 与 GUI Aggregate Report 使用不同公式时可以不同；本研究目标是 Dashboard 既有口径，不能混用 GUI 百分位。

### 可行性与拟议方案

结论：技术原理可行，需固定程序做聚合计算，不是直接读取现成 TPS 字段，也不是 Agent 按总行数估算。官方 Dashboard 本身已提供逐样本聚合逻辑，可以优先调查复用 5.6.3 的统计组件／最薄本地包装；若另写统计模块，应明确复现的口径并进行对照验证，不能因为公式相同就宣称产品资格通过。

拟议流程：采样进程真实结束并保留完整 JTL → 固定轻量统计与输入核验 → 每轮结构化指标 → 寻峰决策；官方 Dashboard 单列生成／交付。Dashboard 具体生成时机、等待／失败策略及报告与轻量指标差异处理，尚需用户决定。

相较完整 Dashboard，轻量步骤可以只统计必要目标指标，不绘制全部图表或建立错误消息明细；减少工作量是设计推断。没有性能基准，不承诺具体时长、速度提升比例或此次卡住根因已修复。后台生成 Dashboard 与下一轮发压并行可能竞争压测机资源，生成时机应后续明确，不能因“独立步骤”自动采用并行。

### 进入替代实现前的必要资格（建议，未确认需求）

- 首期限定可核对的普通逐样本 CSV；有效表头／分隔符／时间戳配置、目标 label、success 和 elapsed 等必需数据齐全。缺字段、聚合 JTL 或截断等不可静默当成正常结果。
- 采样真实结束后统计，不能凭文件暂时不增长认为数据已完整。
- 绑定同一个源 JTL 与实际任务配置，样本数／错误数逐项一致，TPS 时间范围一致；P90 使用同一窗口、估计类型、样本范围和读取顺序，对浮点序列化差异另定合理比较方式。
- 使用同一组正常、高错误率、断言失败、超过 20000 样本及时间边界的合成数据做轻量结果与官方 -g 输出对照；真实 JMeter 生成和速度验证需后续明确授权。
- 总体结论：具备实施依据但尚未实现、未做运行或性能验收；没有修改指标权威、配置、正式需求或产品代码。

本轮主资料均已成功读取；CSVSaveService 长文本的两次 web.find 未定位到文本，已使用可读的官方 CSV 字段手册和 Sample/统计源码证实相关事实，没有依据未定位的页面作出结论。工作区文件清单未查到可直接使用的 .jtl 样本，本轮不读取历史业务结果或凭据，不发送接口请求。

## 2026-10-14 补充：500 并发、74% 错误率能否估算报告耗时

问题来源：用户提出该实际现象并询问大概多久生成报告。此处是事实研究；不是超时规则或等待上限的用户确认。

### 结论及证据

**不能仅据两个数值给出可信的分钟范围。**并发数与错误比例不能确定总样本数、输入字节量、每条消息长度、唯一标签和错误类型数、图表配置或机器资源，更没有本机同配置耗时基准。查到的一手手册和源码没有给“500 并发／74% 错误率”对应的固定生成时长。

- [5.6.3 ReportGenerator](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/core/src/main/java/org/apache/jmeter/report/dashboard/ReportGenerator.java)，181–246 行：先配置样本处理链、遍历图表配置、运行 CSV 样本源，然后导出数据。报告耗时包含读取／统计／图表处理与导出；没有输出文件变化不能单独证明计算停止。可用的内部阶段日志部分是 DEBUG，不保证既有 INFO 日志含每一阶段。
- [5.6.3 ErrorsSummaryConsumer](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/core/src/main/java/org/apache/jmeter/report/processor/ErrorsSummaryConsumer.java)，83–105 行，结合 [AbstractSummaryConsumer](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/core/src/main/java/org/apache/jmeter/report/processor/AbstractSummaryConsumer.java)，84、212–220、246–254 行：错误按响应码／消息或符合条件的断言消息分组，每个唯一键保存汇总数据并生成行。从该结构推断，同为 74% 的错误，固定一种 403 与大量不同／很长的错误消息的处理负担可以不同；不证明用户本次就是分类膨胀。
- [5.6.3 JMeter 合并模式结束逻辑](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/core/src/main/java/org/apache/jmeter/JMeter.java)，1185–1218 行：先收尾，再在生成前记录 `Generating Dashboard`，成功返回后记录 `Dashboard generated`，异常则记录生成错误。两条成功日志之间的时间可作为该次合并模式报告生成耗时证据；从配置压测时长到整个命令退出不能准确替代它。独立 -g 路径不能假定沿用同样两条日志，应由固定执行器另行记录启动和真实退出，并结合实际日志及产物核验。
- [官方 GUI 报告章节](https://jmeter.apache.org/usermanual/generating-dashboard.html#report_gui) 提到超过两分钟调整 GUI generation_timeout。它不是报告应在两分钟内完成的 SLA，也不是 CLI 已提供的等待上限。

本机 `bin/jmeter.bat` 条件默认 HEAP 是 Xms1g／Xmx1g／MaxMetaspaceSize256m，已只读核对；这不代表用户所述那次运行的实际内存设置，外部环境和启动配置可能改变它。本轮没有调整 Java 内存、日志级别、报告图表或其它参数。

### 解释示例（假设，不是基准）

同为 500 并发和 74% 错误，若实际采样跨度 180 秒、TPS 分别是 100 与 3000，总样本数约为 18000 与 540000，相差 30 倍。由此只能说明两项输入不足以确定处理量；不能按 30 倍线性承诺报告耗时。快失败可能增加样本产量，也可能是慢超时导致少量样本，未见实际数据不能代判。

### 建议的判断顺序与尚缺证据

1. 先核实到底已进入 report 生成、仍在采样／收尾，还是生成已失败；读取该次 JTL 与 JMeter／控制台日志的实际位置。
2. 获取 JTL 文件大小和有效样本规模、普通 CSV 保存／报告配置、唯一标签与错误分组情况。只持久化必要统计摘要，避免记录原始 Cookie、认证数据或响应正文。
3. 若正在生成，CPU、内存／垃圾回收、日志与导出情况可作为仍在处理或资源压力的线索；单一线索不证明卡死，也不能把日志暂时无新增等同于没有进展。明确失败／真实退出优先于等待时长。
4. 估算与等待上限应使用同机、同配置、相近输入的实际生成耗时，再由用户确认容忍时长。当前未运行这样的基准，不推荐固定 5／10 分钟数值或默认“十分钟必卡死”。

用户本次尚未给该次输入与日志路径。本轮不查遍用户磁盘、不发送请求、不补跑负载或生成报告；下一步询问最小必要的路径信息，只读核对后再讨论等待策略。若原始材料不在本机，只能依据用户提供的脱敏摘要作有限分析，不能冒充本机复核。

## 2026-10-14 补充：不发送原始文件时的本机进程诊断

用户表示不能提供材料，询问其他判断报告生成是否卡住的办法。本轮是机制研究和有限环境核对，没有向任何 JVM 发诊断请求、列举实际 JVM 命令行、采集线程快照或操作进程。

### 一手依据与判断边界

- [JDK 17 Hangs and Loops 指南](https://docs.oracle.com/en/java/javase/17/troubleshoot/troubleshoot-process-hangs-and-loops.html)：先结合 OS 的 CPU 活动，再取得线程转储。忙碌进程也可能是循环；低活动进程可能在等待。线程转储可报告检测到的 Java 级死锁；没有检测到死锁不排除其它等待或逻辑问题。定时没有日志／文件变化不能自动等同死锁。
- [JDK 17 jcmd 手册](https://docs.oracle.com/en/java/javase/17/docs/specs/man/jcmd.html)：对确切 PID 使用 Thread.print 可取得线程栈，-l 带并发锁信息；该命令影响等级为 Medium，取决于线程数。必须在目标 JVM 所在机器、相应用户权限下使用。不能使用 PID=0／宽泛主类匹配去诊断所有 JVM。工具不存在、附加失败或诊断超时，应记“诊断不可用／不确定”，不能据此认定报告进程卡死。
- [JDK 17 jstat 手册](https://docs.oracle.com/en/java/javase/17/docs/specs/man/jstat.html)：可观察垃圾回收计数与时间，含 Full GC 次数／时间和总 GC 时间。计数或耗时增长是 GC 活动／资源压力线索，不能单凭它们证明报告仍有效推进或已经内存不足。
- 当前 runner 的 process.py 通过 cmd 包装器启动 .bat；本机 JMeter5.6.3 的 jmeter.bat 第200行再启动 Java。需要绑定本任务的确切 Java 子进程及创建身份，不能把 cmd/Python 外壳活动当作报告 Java 活动，更不能选择任意 java.exe。

### 本轮实际环境核对

当前 PATH 的 java 是用户 jdk-17/bin/java.exe。PATH 未找到 jcmd/jstat；只读列举该实际 Java 目录的 j*.exe 后也未找到这两项。这只说明当前 PATH／所用目录未发现，不宣称整台电脑不存在其他完整 JDK，更不代表同事环境也相同。本轮没有下载安装、调整 PATH 或环境变量。

Microsoft TotalProcessorTime 的在线文档打开失败，本轮不据该失败页面确认具体采样 API；OS 指标的实现选择和累计值差分仍需要在后续架构／测试中核验。基础 CPU 检查的原则由上述已读 Oracle 指南支持。

### 拟议首期方案（需用户决定，不是已实现能力）

1. 独立报告入口保存启动／退出证据，标识实际生成 Java 进程；在本机采集少量活动指标和可用的阶段／产物变化摘要。
2. 明确退出后产物不合格，按生成失败处理；进程存活且有活动，只能报告“有活动”，不能承诺正常进度百分比或剩余分钟数。
3. 多次观察低活动且没有阶段／产物推进，可报告“疑似无进展”，提示用户；时间间隔和阈值应作为工程策略另定，不当成官方卡死阈值。CPU高、同一栈也可能是大批计算或循环，需上下文分析。
4. 有经核对的 JDK工具时，再用有限次数线程快照／GC观察增强诊断；缺工具采用基础状态和未知，不自动新增依赖。不是常规每秒打印全部线程，也不做堆转储或触发 full GC。
5. 诊断只影响告警与人工参与；不能修改官方 TPS/P90/错误率，不因此自行终止、重发或复验。终止／等待上限策略仍是独立未决项。按已验证的宿主机制投递问题；后续问题可在首问题答复后展示，不能承诺新即时推送能力。

本机诊断可以避免外发原始 JTL，但当前没有这个实际案例的进程／线程证据，仍不能给出该次卡住的根因或报告预计耗时；上述机制没有经过集成验收。

## 2026-10-14 补充：停止操作与真实退出的证据

本次仅补查一手资料，以支持“用户选择停止但无法确认退出”的业务分支；没有向进程发停止命令或执行诊断。

- [Microsoft Process.WaitForExit 文档](https://learn.microsoft.com/en-us/dotnet/api/system.diagnostics.process.waitforexit?view=net-9.0)，164–168、194–196行：有限等待返回值区分进程已退出／未退出，停止请求没有被执行而进程未退出时也不能记为退出。这是公开进程 API 的行为依据，不代表 runner 已使用 .NET、不新增 .NET 依赖，也不证明当前 Python／Java 进程树停止适配已通过。
- [Microsoft taskkill 文档](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/taskkill)，34、50–53行：按 PID 与按映像名称是不同选取方式，/T 的对象为指定进程及其启动的子进程。从这一作用范围推断，停止主监督任务与仅停止一轮独立报告不是相同操作，不能用终止主任务替代报告专用控制。文档不证明某次具体命令已经成功，也不解决 PID 复用的身份核验。
- 本场已读取的 candidate/references/workbuddy-host.md 明确：监督器可能来不及保存 exit；缺退出记录应是 running-or-unknown，status 不证明任意 Java 子孙已退出。对应新独立报告步骤，需要结合准确身份和实际 OS 退出证据，在后续受控宿主集成测试中核验。

设计推断：无法确认报告生成进程退出时，不能直接开始下一请求，否则会违反已确认的串行边界并可能与旧生成过程争用压测机资源。等待人工核实后继续与结束整次任务是用户的处理选择，研究本身不替用户决定。没有对异常概率作实测估算，不宣称本次已经出现该异常。

两份页面本次成功读取到相关正文。没有下载、安装、更改进程 API、内存、权限或产品代码；本节不确定具体停止实现、等待秒数及自动重试次数。
