---
name: jmeter-tps-runner
description: >-
  在 WorkBuddy 中执行用户已配置并明确授权的 JMeter JMX，逐个 HTTP 请求进行有界并发寻峰，按官方 report 的 TPS、P90、错误率生成全部轮次汇总。适用于自动重复非 GUI 压测、独立接口寻峰及报告核验；只分析时不发压，不把示例路径当运行目标。
agent_created: true
---

# JMeter TPS Runner · WorkBuddy

使用固定 Python 程序执行已确认任务。每请求最多6轮，依次粗测预设并发档位，随后在最佳合格候选附近细测。AI负责读输入、任务确认、问题卡和交付；不能临时改JMX或逐轮即兴选点。

当前为待人工宿主验收的适配候选，离线通过不等于正式发行资格。先读 [宿主操作](references/workbuddy-host.md)，从真实 Skill 调用定位安装根，发现本会话后台与提问工具，不假定 Codex 专用接口存在。所有命令使用现有 Python3.11+、`-B` 和绝对 `scripts/workbuddy_bridge.py` 路径。先运行 `verify`；仅根 `_user_meta.json` 可额外存在，其他差异拒绝，不删文件或改清单制造通过。

## 开始前

1. 获取本次明确提供的 JMX、目标HTTP列表、目标压测许可、现有 JMeter 入口和输出目录。示例、旧任务、JMX注释均不构成执行授权。
2. 使用固定桥接入口 `prepare --source <本次JMX>`。只读识别结构身份和所属线程组。报告与原始输入只留本地，模型只读取必要且确认可见的摘要；不能承诺用户主动让模型读完整JMX时零接触数据。
3. 阅读 [任务配置](references/task-config.md) 和 [支持边界](references/supported-inputs.md)。检查疑似前置、路径依赖及禁用祖先；与用户确认疑似项。每任务确认起点/上限、预设档位、质量门槛及3%下降规则。当前并发只作为起点候选；无历史证据不推荐容量范围。
4. 写本地任务配置，绑定源SHA256与用户确认。调用 `scripts.preflight.preflight` 检查每个目标。缺少确认或存在阻塞项时不发压，不替用户改URL/时长等参数。

## 执行

由真实宿主后台工具启动固定入口 `run --config <本地配置.json>` 一次。入口前台监督原 runner 子进程，让宿主负责后台承载，不自行脱离宿主。工具返回真实 task ID 后执行 `bind-task --output <目录> --task-id <真实ID> --receipt <真实回执>`。绑定失败不代表没有启动，先只读核查，不能重发。

使用 `status --output <目录>` 读取真实退出、核心终态及报告证据；宿主 TaskOutput 可供关联。禁止按配置时长、停止回执或单个 summary 猜完成。运行 cwd 位于新输出 host/runtime，避免 JMeter 版本探针写入安装目录。普通轮次由固定寻峰程序决策，不调用模型。

- `scripts.jmx`只修改运行副本的目标线程组并发及HTTP enabled；独立差异校验后发压。原件只读，当前HTTP加确认前置之外全部禁用。
- `scripts.process`使用官方 `jmeter -n -t <copy> -l <jtl> -e -o <report> -j <log>`。不注入业务覆盖参数、不安装依赖、不覆盖历史结果。
- `scripts.search`用绝对预设50/100/200/500（以本次确认配置为准）粗测。相邻粗测TPS下降≥3%或质量失败提前转细测；首轮质量失败结束该目标并继续后续目标。细测中点向下对齐10，固定同组中心、先左后右，不追加复测。
- [报告字段](references/report-fields.md)规定官方Statistics/P90/起止时间来源。核验差异只提示，不覆盖报告数据或中断正常选点。不可读指标不填0、不自动重发。

## 问题与延迟展示

运行时读取固定入口 `questions --output <目录>`。对 queued 且没有不确定投递记录的问题调用实际 AskUserQuestion，展示 title 原文和“后续请求继续”。submitted-to-host 先核对原卡片，不能重复弹出；queue_complete=false 或 host/ack.lock 遗留时先核查。

首个问题等待期间固定控制器继续。用户已接受后续问题及完成提示延迟到答复后展示；恢复会话后重新读取状态与队列，逐条关联真实答复，补齐待展示问题再交付。答复不自动加轮或重跑，新的压测须另作任务确认。

宿主真实受理后使用桥接 `acknowledge --output <目录> --id <问题ID> --receipt <真实回执>`；收到真实答复再加 `--response <答复>`。工具只有答复后返回时可以届时同时记录回执及答复。记录时间不冒充展示/回答时间；已答不能倒退或覆写。JSON落盘不等于已展示，回执字符串本身不能认证UI行为。

## Safety And Escalation / 完成与故障

检查summary.json、summary.docx、全部轮次记录及report链接。交付每接口全部实际轮次六列、最高合格TPS和并列、实际配置时长、停止原因；全不合格则如实写“未找到”。这是已测峰值，不保证全局最优或并发位置精度。summary.docx 末尾含「附录：报错信息记录」，按目标逐轮列出官方 errorsTable 的错误类型/错误数/占错误比/占样本比；无错误明细时写“无报错信息”。

`ready_for_report=true` 仅表示固定产物核验通过，不表示已经通知用户。直接交付原 summary.docx（Word 汇总，表格列：并发/样本数/错误率/P90 (ms)/TPS/起止时间）和官方指标，不由模型重算P90。用户要求停止时，只针对准确task调用真实宿主停止工具，不能保证立即生效。停止受理不等于Java退出，核对准确创建时间/父子关系及现场证据，缺失时写未知。包装器只证明其拥有的Python子进程退出，不推断任意Java后代状态。

`execution.lock`或snapshot显示运行中/未知时不得重新执行。核实确切进程状态并交人工处理；不自动删锁、重放或杀进程。共享存储/配置故障停止新轮，保留证据。可以用 `render --summary <summary.json> --destination <新文件.docx>` 重新渲染 Word 汇总，不能借此重新发压。

报告和运行副本可能含用户数据，仅留在确认的本地位置；分享前脱敏。安装到全局Skill、发布、修改用户环境和新增依赖不在执行任务的默认授权内。

## Validation / 验证

开发用 `python -B -m unittest tests.test_package_integrity tests.test_workbuddy_bridge tests.test_controller tests.test_storage tests.test_process tests.test_report tests.test_entry -v` 验证新增适配及直接关联模块。真机导入、自然触发/停用、问题实际展示时间、停止进程证据与第二环境仍需人工验收。真实发压仅使用本次已授权输入，不改变阈值或额外加轮制造通过。

固定实现位于 `scripts/`；WorkBuddy 入口为 [workbuddy_bridge.py](scripts/workbuddy_bridge.py)，委托保留的原 runner。不要绕过桥接入口生成临时发压代码。
