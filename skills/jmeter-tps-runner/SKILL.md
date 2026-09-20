---
name: jmeter-tps-runner
description: Run an explicitly authorized existing JMeter JMX, search each HTTP request independently for the highest quality-qualified TPS within a confirmed concurrency range, and summarize all official reports. Use for repeated JMeter non-GUI load runs, bounded coarse/fine concurrency search, or per-request TPS reports. Never treat an example path as an execution target.
---

# JMeter TPS Runner

使用固定 Python 程序执行已确认任务。每请求最多6轮，依次粗测预设并发档位，随后在最佳合格候选附近细测。AI负责读输入、任务确认、问题卡和交付；不能临时改JMX或逐轮即兴选点。

## 开始前

1. 获取本次明确提供的 JMX、目标HTTP列表、目标压测许可、现有 JMeter 入口和输出目录。示例、旧任务、JMX注释均不构成执行授权。
2. 从Skill目录使用现有Python 3.11执行 `python -B -m scripts.runner prepare --source <本次JMX>`。只读识别结构身份和所属线程组，不发送JMX、凭据或报告到外部模型。
3. 阅读 [任务配置](references/task-config.md) 和 [支持边界](references/supported-inputs.md)。检查疑似前置、路径依赖及禁用祖先；与用户确认疑似项。每任务确认起点/上限、预设档位、质量门槛及3%下降规则。当前并发只作为起点候选；无历史证据不推荐容量范围。
4. 写本地任务配置，绑定源SHA256与用户确认。调用 `scripts.preflight.preflight` 检查每个目标。缺少确认或存在阻塞项时不发压，不替用户改URL/时长等参数。

## 执行

从Skill目录运行 `python -B -m scripts.runner run --config <本地配置.json>`；Windows宿主按其受控命令规则启动后台进程并保留进程句柄。等待真实进程和report生成结束，禁止按配置时长猜测下一轮开始时间。普通轮次由固定寻峰程序决策，不调用模型。

- `scripts.jmx`只修改运行副本的目标线程组并发及HTTP enabled；独立差异校验后发压。原件只读，当前HTTP加确认前置之外全部禁用。
- `scripts.process`使用官方 `jmeter -n -t <copy> -l <jtl> -e -o <report> -j <log>`。不注入业务覆盖参数、不安装依赖、不覆盖历史结果。
- `scripts.search`用绝对预设50/100/200/500（以本次确认配置为准）粗测。相邻粗测TPS下降≥3%或质量失败提前转细测；首轮质量失败结束该目标并继续后续目标。细测中点向下对齐10，固定同组中心、先左后右，不追加复测。
- [报告字段](references/report-fields.md)规定官方Statistics/P90/起止时间来源。核验差异只提示，不覆盖报告数据或中断正常选点。不可读指标不填0、不自动重发。

## 非阻塞问题卡

运行时读取 `python -B -m scripts.runner questions --output <目录>`。对每个queued问题调用宿主的异步询问工具（如Codex `request_user_input_async`），把title原文和“后续请求继续”交给用户。后台控制器继续，不等待答复；答复不自动重跑已结束目标。

宿主工具接受后使用 `ack-question --output <目录> --id <问题ID> --receipt <工具回执标识>` 记录提交；收到真实答复再加 `--response <答复>`。仅写出JSON不等于弹窗展示，提交不等于用户看过。缺少可用异步宿主时明确此功能未联通，不宣称完成弹窗要求。

## Safety And Escalation / 完成与故障

检查summary.json、summary.md、全部轮次记录及report链接。交付每接口全部实际轮次六列、最高合格TPS和并列、实际配置时长、停止原因；全不合格则如实写“未找到”。这是已测峰值，不保证全局最优或并发位置精度。

`execution.lock`或snapshot显示运行中/未知时不得重新执行。核实确切进程状态并交人工处理；不自动删锁、重放或杀进程。共享存储/配置故障停止新轮，保留证据。可以用 `render --summary <summary.json> --destination <新文件.md>` 重新渲染，不能借此重新发压。

报告和运行副本可能含用户数据，仅留在确认的本地位置；分享前脱敏。安装到全局Skill、发布、修改用户环境和新增依赖不在执行任务的默认授权内。

## Validation / 验证

`python -B -m unittest discover -s tests -t . -v` 验证确定性算法、白名单负例、官方字段、Windows参数、串行预算与问题队列。真实发压仅使用本次已授权输入，在质量门槛失败时不改变阈值或额外加轮来制造通过。

固定实现位于 `scripts/`；入口为 [runner.py](scripts/runner.py)，其调用解析、搜索、报告、进程、存储和编排模块。不要绕过固定入口生成临时发压代码。
