> 公开投影：业务规则与原编号保留；“本轮”指源文档编写阶段。源哈希、路径适配与当前发布范围见 jmeter/docs/publication-context.md 及导出清单。

# 联合接口与状态契约 v0.1

日期：2026-10-14。**以下为拟开发接口，不是现有 CLI 可执行说明**。writer 的原 TaskInput/AuthContract/ValidationResult 语义沿用原规格；本页集中给出联合版本的补充和覆盖部分。精确源位置见 [改动范围](change-scope.md)。

## 1. 角色与公开入口

所有固定入口以 UTF-8 JSON 文件传递任务数据，秘密值不进入命令行。绝对脚本入口可从任意 cwd 使用；任务内相对输入以该任务文件目录解析，执行副本和生成产物使用已经核对的绝对位置。

| 入口（拟名） | 责任与输出 | 执行边界 |
|---|---|---|
| writer analyse / build | 分析来源；生成正式 JMX、模板、角色/依赖及转换差异 | 不执行收到的 Bash。已有 JMX 保留原件，不按新脚本规则重建。 |
| writer probe-auth | 缺提取依据时一个验证账号的一次实际预登录 | 现有依据充分则 0 次；与后续 JMX 试跑分别计数，失败停止。 |
| writer validate | 逐目标试跑、副本差异、JTL/日志、各层结论及交付说明 | 业务 1/0/1，必要单账号隔离；失败停止本次验证，不用 runner 正式 run 代替。 |
| runner check-input | 正式原件/依赖/认证契约与指定消费者的 ready / rejected / unresolved 结果 | 只读，不创建 Store、输出预约或版本探针日志，不启动 JMeter。运行版本资格在已准备的正式任务位置检查。 |
| runner configure-root | 显示或保存工程师首次明确选择的根 | 保存在用户配置区，Skill 包外；不迁移旧任务、不猜作者路径。修改现有根需工程师明确新选择，不静默修复失效根。 |
| runner prepare-task | 验证根/配置，排他分配唯一任务及请求目录，返回 TaskReservation | 只有这个入口分配正式 output。尚未发压，保留预约后不能把重入当成无状态新任务。 |
| runner prepare-round | 针对选出的实际 target / concurrency / round 准备 report、result、plans，返回 RoundPaths | 必经固定前置脚本。controller 通过同一脚本调用；缺准备证据或目录失效不能直接构造路径发压。 |
| runner run（宿主桥接） | 认领 TaskReservation，监督唯一正式控制器，保存真实子进程结束 | 只接受当前确认与源 hash，认领失败不重放；后台由 WorkBuddy 承载，不自行脱离宿主。 |
| monitor run | 任务级观察，正常轮次接续；长等待或不能继续观察时落摘要并退出 | 一个独立原生后台任务；不生成 report、不分析卡死、不发停止指令。 |
| bridge bind-task / bind-monitor | 分别绑定真实主 task ID、监控代次 task ID 及宿主回执 | 主绑定与监控绑定分别保存；不能互相覆盖；绑定未知先查实际任务，不能重起主任务。 |
| bridge status / monitor-status / questions | 组合读取主执行、报告、监控、队列与交付状态 | 文件存在/PID 存在不代表完成；不读取原始秘密作为状态正文。 |
| bridge acknowledge | 记录原问题真实受理/答复及关联 | 仍然不控制进程，不自动加轮。报告停止另走 control-report。 |
| bridge control-report | 记录并提交用户对确切 report 的 stop 请求，返回 request_id/受理状态 | 主控制器持有实际报告范围并执行；客户端不按任意 PID 直接杀 Java。 |
| bridge verify-report-exit | 请求仍活动的主控制器重查原报告退出证据 | 只重新观察，不再停止、不重启；未知仍等待，不接受用户手填 exited=true 作证明。 |
| runner render | 从已核验结果生成新的 Word 汇总 | 不重新采样、不补生成 Dashboard，不覆盖原交付。 |

命令处理 exit 0 表示返回了结构化结果，不能据此把 failed / unresolved / waiting 状态写成产品通过。内部异常无法给出可信完整结果时返回非零。结果必须区分 operation_status、domain_status 与 evidence；固定脚本的参数/协议错误不启动 JMeter。

## 2. 版本与兼容识别

| 契约 | 版本与最小字段 | 兼容策略 |
|---|---|---|
| WriterTask | writer-task-v1；task_id、mode、source、requests、formal、authentication、trial、runtime、consumer、output_dir、authorization | 沿用原字段及条件必需性，未知协议拒绝；不添加正式寻峰参数。新计划正式 Ramp-up/时长由工程师提供。 |
| AuthContract | auth-contract-v1；source_sha256、stages、结构/提取/模板/CSV绑定、formal_account_count、适用目标 | 静态旁文件，无秘密值；绑定正式原件。模板/参数/源改变重新检查，不凭文件名识别角色。 |
| ConsumerCheck | consumer-check-v1；source及hash、targets、普通前置、认证绑定、输出上下文、可选契约ref/hash | 返回实际 consumer_identity、protocols、capabilities、精确 HTTP 集合、依赖、blocking/confirmation 项。检查接受不授予运行权限。 |
| RunnerTask | runner-task-v2；沿用原 task_id/source/source_sha256/jmeter/minimum/maximum/presets/error_percent/p90_ms/decline_ratio/targets/confirmed/authorization_note；增加 root_profile_ref/root_profile_sha256、reservation_ref、可选 auth_contract_ref/hash | output 由 prepare-task 生成并写入已确认快照。旧输入由显式规范化路径转换，仍需根配置/预约，不能用旧 output 绕过固定根；旧结果仅供旧读者或只读查看，不迁移历史。 |
| RoundPaths | round-paths-v1；run_id、target_id、round_id、round_number、concurrency、task_root、plan/jtl/report及各日志位置、reservation/receipt hash | 路径全部在绑定任务内；receipt 只是准备依据，不是许可或“已执行”证据。 |
| StageExecution | stage-execution-v1；stage_id、kind=sampling/report、run/target/round、源plan/jtl hash、profile指纹、启动意图、实际启动/结束、进程归属和退出证据 | 每个实际阶段一个 ID，自动重放不存在；sampling 与 report 分开记录。 |
| MonitorHandoff | monitor-handoff-v1；run_id、monitor_id/generation、原生task绑定、reason、report_ref、提醒记录ref、当前revision、真实退出关联 | reason=long_wait/task_ended/observation_unavailable。后两者不是长等待，不诊断报告。来源记录和宿主完成证据分别核对。 |
| ReportControl | report-control-v1；request_id、run_id、report_id、stage_identity_digest、action=stop、question_id、用户决定/真实回执引用 | 拒绝未知动作/字段；request_id 排他且幂等。同 ID 不同内容拒绝；重复停止不再次执行，旧报告已结束返回 stale_noop。 |
| ValidationResult / TaskSummary | writer-validation-v1 / runner-summary-v2 | 前者沿用三层结论；后者保留原字段，加阶段、认证和搜索状态。读者识别版本，不能把旧 execution 一次退出解释成两个阶段已退出。 |

能力名拟为 consumer-check-v1、auth-contract-v1、split-report-v1、root-layout-v1、report-control-v1、monitor-handoff-v1。writer 的兼容结果绑定实际安装/候选及其清单摘要，不能单看包版本数字。旧消费者无新增能力时明确返回拒绝/未知；无认证的旧标准计划在新版中仍受支持，目录与报告新流程不降级回合并命令。

check-input 的 input_status（结构/组件/依赖/拟定布局是否可接收）与 execution_readiness（未来正式任务根、负载、质量与许可是否已确认）分别返回。writer 需要前者的真实接收结论；尚未首次配置 runner 根或尚未确认正式负载只列“正式执行前置待完成”，不单独把可接收脚本判成认证/业务失败。布局检查使用只读的预期规则/明确上下文，不能为了得到 accepted 静默创建真实任务或代选根。正式 run 仍必须满足全部执行前置。

## 3. 目录、根配置与预约

提议本机根配置为 `%LOCALAPPDATA%/jmeter-tps-runner/config/output-root.v1.json`，只记录 schema_version、output_root、首次用户选择引用、updated_at 与 revision。默认的是**配置落点**，不是输出根值。此为本次技术选择，未写入本机。writer 的编写/短验证输出仍用其本次明确目录，不强制继承 runner 用户配置。

任务目录名使用可读时间加随机唯一后缀，逻辑 task_id 与实际 run_id 区分。排他创建是最终防重依据，时间相同不覆盖。HTTP 名保留可读部分，沿用 Windows 字符规整与结构身份后缀。

```text
<已确认根>/<自动任务名>/
  allocation.json                 # 唯一任务预约，尚非执行成功
  task.json / events.jsonl / snapshot.json / progress.json
  questions/                     # 原问题与真实答复
  host/                          # 主监督/原生绑定/真实退出
    monitor/<代次>/              # 每个监控的绑定、摘要、退出关联
    monitor/reminders/            # 按 report_id+kind 排他生成的提醒
    control/                      # 控制请求与主控制器结果
  <HTTP名--身份后缀>/<并发>/
    plans/run-NNN.jmx
    plans/run-NNN.<stage>.cookie.csv / auth.json  # 自动模式的限定本轮产物
    result/result<并发>-run-NNN.jtl
    result/sampling-run-NNN.log / .console.txt
    result/report-run-NNN.log / .console.txt
    result/run-NNN.prepare.json / .sampling.json / .report.json / .round.json
    report/run-NNN/               # 启动前存在且为空，准备证据不放在这里
  summary.json / summary.docx
```

TaskReservation 至少绑定 root_profile 摘要、规范化根、run_id、task_id、唯一 output、目标清单/源/配置摘要、created_at。主入口只认领一次；现有目录仅在符合本次预约且尚无启动认领时可接收，替代旧桥接“一律拒绝 output 已存在”的判断。发现旧 task/events/执行意图或冲突认领，拒绝启动；不是删除锁后再试。

prepare-round 校验预约、目标身份、选出并发、轮次及实际路径。report/run-NNN 排他创建为空；JTL/plan/log/console 不存在。父目录可为同一目标已准备结构，但已有本轮文件或不一致 receipt 不允许覆盖。检查目录重解析/链接、源别名、根内归属及名称冲突；不创建未选档位。采样/报告启动前再次核对，不能仅相信一次返回值。

首次配置缺失时等待用户给出真实根。根配置损坏、不可写、目录被占用或准备失败，返回 directory_prepare_failed 并停止新轮；保留已有结果，不切到临时目录。准备本身不记已采样轮次。用户输入/原件可以在根外，运行产生的副本、认证文件和结果不得逃出根。发现原计划存在无法满足此边界的额外写入配置时报告具体兼容缺项，不代改原件。

## 4. writer 编写、Cookie 与短验证

原接口中的 cURL 支持表、静态头保留、默认 JSONPathAssertion、手工/自动/其他认证判断均沿用。优先 Python3.11+ 标准库编排和本机 5.6.3 解析器薄适配，Java helper 的构建/分发先过 G-01，不要求使用者现场安装 JDK 或编译，不上传 cURL 到外部转换服务。

新 Cookie CSV 的具体格式提议沿用原规格：UTF-8 无 BOM、表头 cookie、每行完整 Cookie 请求头值，变量 cookie；新建原生 CSV 显式 Recycle=true、StopThread=false、Sharing=All threads。原有 CSV 保留实际列、编码、表头、引号、共享/EOF 策略，仅为验证隔离替换对应认证 filename。缺值/不支持隔离如实未验证，不擅自重写配置。

自动 AuthContract 的重要绑定包括：认证组/登录 HTTP 结构身份、账号输入 CSV 节点/格式/数量、提取器及 Cookie 名来源、固定前/后处理模板 ID/摘要/参数、生成文件生产者、限定属性/CSV消费者、applicable_target_ids。业务 targets 仍为标准组下 HTTP；setUp 登录不列入业务目标。普通业务前置仍为已确认的同组同执行上下文先行请求。

正式源的 N 账号循环来自当前材料；试跑副本只使用选中单账号数据，并将必要认证循环配置改为 1。固定模板根据**执行副本的受控有效认证循环配置**识别本轮期望数，不能把原件 N 写死后导致试跑仍等 N 条；该点在 G-02 实测，不通过则不接受自动模式。验证上下文分别记录 formal_source_sha256、trial_copy_sha256 与允许覆盖清单，不把试跑 hash 冒充原契约源。

固定认证构件保持脚本文本/限定参数资格，附着在登录 HTTP 下，业务组原生 CSV 读取本轮发布文件。全部期望账号完成且流关闭后才完整发布；失败不回退旧文件。正式每轮依据当前执行 JMX 的基准与文件名派生不同输出，并绑定唯一执行身份。不能用旧 cookie.csv、旧 complete 标记或仅文件时间证明本轮认证。

动态路径只资格限定属性表达式与生产者/消费者关系，绝不普遍放行动态文件。**非当前业务组仍存在于副本中的原生 CSV 初始化行为是 G-02 必测项**：不得打开无效引用、消费旧轮、触发无关登录或使当前目标失败。如果拟定结构做不到，停止自动模式验收并修订生成结构；不能默默修改组 enabled、脚本或正式 CSV 路径绕过。

writer validate 的 execution、authentication、assertions、consumer 状态及优先级沿用：真实失败/明确拒绝→failed；缺必需材料→needs_input；未知/未覆盖→unverified；仅旧缺业务断言→ready_with_warning，明确业务断言未验证；适用必需检查全部满足→ready。预登录最多一次，完整试跑另计；实际验证失败后不启动剩余目标。

## 5. 正式轮次与执行接口

controller 保留 run 作为最高业务边界，将原 executor 扩展为一个阶段化执行适配器：execute_sampling、execute_report、observe_report、request_report_stop。适配器可注入，内部 Windows API 不成为普通业务用例的测试入口。存储准备以同一固定脚本调用，测试允许替换其结果验证“准备失败时调用为零”，生产不允许自由替换执行脚本。

| 顺序 | 输入/动作 | 允许继续的完成条件 |
|---|---|---|
| 1 | 原 search 决策得到并发，强制 prepare-round | 当前绑定的独占路径已准备，源/根/预约不变。 |
| 2 | 生成正式副本，独立解析比较 | 只改当前标准业务组 num_threads 与精确 HTTP enabled；目标＋必要认证＋普通前置，原件不变。 |
| 3 | 先持久化 sampling 意图，再官方非 GUI 采样 | 参数为 -n -t plan -l jtl -j sampling_log，不含合并 -e/-o；没有自行增加业务覆盖参数。 |
| 4 | 核实 sampling 真正退出、记录 JTL 身份/保存配置 | 已拥有进程真实结束、结果可核对；未知不启动 report/下一采样。失败不自动重发。 |
| 5 | 需要时核 AuthenticationResult、账号数、CSV/登录样本 | 分别记认证结果。有完整可报告 JTL 时仍进入 report；认证失败最终不评分。认证证据不改变 JTL/报告数值。 |
| 6 | 持久化 report 意图，启动独立官方报告 | 参数 -g 同轮JTL -o 空report目录 -j report_log；绑定输入 hash、实际保存/报告环境及 report_id。 |
| 7 | 等报告自然退出或处理确切控制请求 | 主程序在等待时仍响应报告控制，不阻塞在不可处理控制的无限 wait；监控另进程观察。 |
| 8 | 验证实际报告范围退出、exit code 与必需产物 | statistics.json、index.html、content/js/dashboard.js，唯一目标行/90th pct 元数据/官方时间。部分文件不够。 |
| 9 | 适用认证通过且 report 有效→官方观测与原算法；否则目标技术问题 | metrics/observation 只有合法评分分支非空；审计只给线索，技术问题按真实退出规则继续后续目标。 |
| 10 | 保存实际 round、progress、目标结果及最终汇总 | 真实已启动采样计 1 轮。只有报告/监控没有再次消耗预算；保留原峰值排序与并列处理。 |

两官方命令使用同一 JMeter 5.6.3 入口、执行基准和已确认环境/相容的保存及报告属性，不通过修改 JMX 或 JVM 内存“修复”报告输入。只记录必要配置指纹/有效非秘密设置，缺关键字段时明确技术问题；扩展名 .jtl 不代表一定是合格 CSV。版本探针的 cwd/日志也在已分配任务下。

## 6. 主状态、轮次状态和交付

| 层 | 状态 | 解释 |
|---|---|---|
| 主任务 | reserved → running → completed / completed-with-technical-issues；另有 waiting_report_exit / failed / unknown | 保留原 completed-with-technical-issues 字面值；waiting_report_exit 仍为活动但禁止发压，unknown 不自动恢复或重放。正常报告等待不等同此状态。 |
| 本轮 | paths_prepared → copy_verified → sampling_start_intent → sampling_running → sampling_exited → report_start_intent → report_running → report_exited → validated → recorded | 意图不证明已启动，进程结束不证明 report 有效。认证检查另字段记录，不能被状态名掩盖。 |
| 报告 | running / stop_requested / exit_unverified / succeeded / failed / stopped | succeeded 还需产物校验才能评分；停止受理不等于 stopped。技术失败/人工停止不写 quality_exceeded。 |
| 搜索 | completed / interrupted_technical / interrupted_by_user / not_started | completed 指按既定预算/停止规则结束，不意味着区间穷举或绝对最优。 |
| 交付 | pending / artifacts_verified / delivered | delivered 需要真实交付依据；主进程退出或 ready_for_report 不等于已展示。 |

RoundResult 增加 sampling_execution、report_execution、authentication_result_ref/status、report_status、search_effect 与 safe_issue；保留 number/concurrency/phase/paths/decision/verification/audit/metrics/observation。无有效评分的 metrics/observation=null，保留 concurrency、round_number 和真实状态，不把整行变成“不可读”。

新 schema 的读取器按明确状态接受未启动目标 rounds=[]，不能继续套用旧桥接“每个目标至少一轮”规则，也不能为凑数生成未采样行。实际已启动的轮次仍为1–6。共享存储故障可能无法完成Word写入，此时只交付能够核对的已有证据及故障，不伪造完整交付。

汇总仍是每接口全部实际轮次、实际配置持续时间、官方开始/结束、并发/样本/P90/TPS/错误率，标最高合格候选/并列和停止原因。Word 及 JSON 均注明被中断搜索；无 report 指标写未完成/原因，JTL 采样时间另标证据来源，不能填成官方起止时间。保留官方错误附录，其 dashboard errorsTable 可能覆盖该轮所有选中样本；标明范围，不将含登录/前置的全轮错误误称为仅目标错误。

## 7. 监控事实与 WorkBuddy 交接

1. 主与监控分别由实际宿主后台启动，各自保存真实 native_task_id。主程序/报告绝不是监控的子进程。
2. controller 单写主 snapshot/events；投影当前 report_id、stage_start、基于同一主进程单调时钟累计的 report_elapsed_seconds、revision 和实际结束状态。监控不改写主状态/事件链，提醒与监控日志使用独立命名空间。
3. 拟主控制循环 1 秒检查控制，报告观察投影与监控轮询间隔 5 秒。它们是工程默认值，不是卡死阈值或即时通知 SLA；测试使用可控时钟，正式长等待阈值固定 600 秒。新监控取原报告投影，不能以自身启动重计。
4. 同一任务监控持有排他运行约束；正常退出释放自身约束并保存摘要。没有真实退出证据、遗留不确定认领或绑定未知，先核查，不能仅按 PID 不存在启动第二个。续建需核对旧 native task 已退出及对应 monitor_id；不重起主任务。
5. report_elapsed_seconds≥600 且原报告仍未完成时，按 report_id+long_wait 排他写一次 reminder，保存 MonitorHandoff 后监控退出。记录 reminder_created 不等于宿主已通知/用户已见；不同事实分别关联真实回执。写提醒/通知中断时保留不确定状态，不换名反复重报。
6. WorkBuddy 收到原生完成→核对 handoff/最新主状态/旧监控退出→主活动时先启动并绑定新监控→再分析/提问。终态不续建，主状态未知先核查，不借此重放。
7. 对同一报告不再因时间重复提醒；新的明确异常可形成不同事实交接，不把旧长等待换名再报。下一报告使用新 report_id 和自己的原始起点。

诊断由 WorkBuddy 读取报告对应 Java 身份、日志尾部和必要活动摘要。已有 jcmd/jstat 可用时只针对确切 PID 有限取证；不自动安装，不作堆转储/触发 GC 的常规流程。若证据不足，明确说“不确定”，仍向用户提供等待/停止选择。用户暂未答复，主报告继续；稍后先重读状态再处理旧答复。

## 8. 报告专用停止与退出待核查

control-report 只写不可变控制请求；**主控制器**核对 request_id、report_id、stage digest、run/config 绑定和当前阶段。用户决定引用是审计证据，不是可自行生成的授权密钥；自动监控不能制造该请求。

| 情形 | 控制结果与后续 |
|---|---|
| 原报告仍运行且身份一致 | 主程序写 accepted，执行一次限定停止并观察退出。 |
| 原报告已自然结束/进入下一轮 | stale_noop，记录迟到答复；绝不按“当前 PID”转投新报告。 |
| 同 request_id 同内容再次读取/提交 | 返回已有结果，不再次停止。 |
| 同 ID 不同内容、其他 run、采样身份或未知报告 | rejected，控制副作用为零。 |
| 真实报告范围退出已核实 | exited_verified，记录 stopped、无评分，结束当前 HTTP，继续下一请求。 |
| 停止调用失败或有限观察后退出不明 | exit_unverified，主任务 waiting_report_exit，后续采样调用数为 0；说明人工核查。 |
| 后续原报告自然退出，主程序仍在并得到真实证据 | 不再发停止；记录事实后继续下一 HTTP。可用 verify-report-exit 促使同一 owner 重查。 |
| 主程序也已中断/身份失效 | unknown，不以手填退出或新起 controller 自动续跑原任务。整任务恢复不在本范围。 |

拟定 Windows 实现：主程序持有**只包含本轮报告包装器/Java 的 Job Object 与进程句柄**，报告启动前建立归属约束，保留创建时间/映像与执行绑定；不使用全局 Java 名称扫描来决定停止对象。使用已有 Win32 能力的薄封装，不新增第三方常驻依赖。子进程归属、启动竞态、WorkBuddy 上层 Job 的嵌套/限制和没有 breakaway 泄漏必须过 G-04；不能因 API 文档存在宣称可用。

停止针对该 report Job，随后核对已持有进程的实际结束和该 Job 无活动成员；不只等待 cmd，不把 Job 的一般 signaled 状态当作“自然结束全部进程”的万能证明。拟观察最多 30 秒后返回 exit_unverified 而**继续保留等待状态**，不是自动超时推进或第二次杀树。该值是一次控制调用的工程等待限值，不是 report 生成上限；真实资格后可记录必要技术调整。

报告Job不设置自动运行时限或以句柄关闭触发终止的策略；报告专用停止由主owner在真实用户决定后显式执行。监控不持有报告控制句柄。主任务被用户 TaskStop 时仍按旧未知原则核对整链，不能推断本轮新增专用停止已通过；新方案不增建整任务恢复器。

## 9. 证据与安全输出

AuthenticationResult 保留 stage/execution_plan、expected/prepared 数、产物摘要/行数、模板身份和安全错误；再绑定实际采样 execution_id。必须结合真实登录样本/断言核验，postprocessor 标 complete 不能覆盖随后断言失败。

完整私有 cURL、账号、Cookie、响应和 JTL 如必要仅存本地授权任务；供模型/同事的摘要不抄秘密。分享包只有模板、代码和格式说明。任何摘要/hash/schema/marker/exit0 只能证明对应检查，不能独自证明登录有效、压测授权或产品完成。文件与目标变化后结论只适用原输入，不复用旧验证当作当前认证通过。
