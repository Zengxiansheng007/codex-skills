---
artifact:
  id: ART-JM-DEV-001
  type: development-plan
  title: jmeter-tps-runner development-plan
  version: v1.2
  supersedes: v1.1
  statusCode: review
  statusLabelZh: 待评审
  reviewStatus: Codex内容核对完成；非新增用户需求批准或RC
  owner: Codex
  upstreamArtifacts: [jmeter-tps-runner-requirement-anchor-v1.2]
  downstreamArtifacts: [jmeter-tps-runner-release]
  createdAt: 2026-09-20
  updatedAt: 2026-09-20
  sourceBaseline:
    sources: [baseline-manifest.json, evidence-index.json]
    fingerprint: 3a6ff756abdfbce1c34ec8f70d808d50366a893a9a422677e5e0eb51187441f3
  riskAccepted: [RISK-001, RISK-002]
  openQuestions: []
  rtmRef: coverage-v1.1.json
---

# jmeter-tps-runner 开发计划 v1.2

本版依据最终源码和已存在的执行证据回顾；仅更新事实、实现边界及追踪，不改变已批准的FR/BR/NFR/AC。历史基线只读保留。文档发布不将历史批准自动转移到新版本，亦不产生RC。

## 1. 执行路线及当前状态

TASK-001由已授权Claude实施后经Codex审查修正；TASK-002的Claude调用失败且无实现改动，保留失败证据后按用户授权由Codex接管；后续本地执行已获授权。执行者完成与Codex验收分别留证据。当前TASK-001～007已完成其限定实现/验证，发布前补做本次文档闭环。

实际复用Python3.11标准库与JMeter官方CLI，不增加运行依赖。已有25个可复用源码/说明/测试文件；版本探针生成的jmeter.log不是源码，公开包排除。源代码本次不改动。

上游为[PRD](prd-v1.3.md)与[架构](architecture-v1.3.md)。代码在../../skills/jmeter-tps-runner/；测试证据见evidence-index.json。

## 2. 文件与接口

以下文件均已实现；表中路径相对Skill根目录：

| 文件（相对Skill根目录） | 责任及架构接口 |
| --- | --- |
| scripts/contracts.py | TaskSpec、TargetIdentity、RunIntent、Observation、SearchDecision；IF-001/002/003 |
| scripts/search.py | 纯确定性选点、失败边界、预算、精确并列；IF-003 |
| scripts/jmx.py | 结构定位、前置候选、白名单差异、完整 HTTP enabled 集合；IF-001/004 |
| scripts/preflight.py | 本次输入、版本、路径依赖、确认项完整性；IF-001/002 |
| scripts/process.py | 官方 n/t/l/e/o 参数、Windows 批处理边界、进程退出；IF-005 |
| scripts/report.py | 版本化 Statistics/P90 与官方起止时间读取；IF-006 |
| scripts/audit.py | 同口径 JTL 核验，独立提示，不改变评分；IF-007 |
| scripts/storage.py | 单写者、独立轮次目录、原件/配置指纹、事件；IF-008 |
| scripts/controller.py | 独占运行槽、串行目标、预算、隔离切换、停止；IF-002/003/004/005 |
| scripts/host.py | 问题事件和宿主交接状态，不冒充已展示；IF-009 |
| scripts/summary.py | 全部实际轮次、六列、官方时段和峰值；IF-010 |
| scripts/runner.py | prepare、run、questions、ack-question、render 固定入口，不接受任意修改脚本 |
| SKILL.md、agents/openai.yaml | 触发、任务确认、固定入口使用、宿主问题卡桥接 |
| references/task-config.md、supported-inputs.md、report-fields.md | 参数、支持范围、版本化字段证据 |
| tests/test_*.py | 与下列任务一一对应的针对性验证 |

## 3. 阶段与独立任务

PH-JM-01（确定性核心）：进入条件为 v1.2 基线及本计划可用、执行者权限满足；退出条件 TASK-001/002 代码经 Codex 审查且离线正反例通过。

PH-JM-02（运行闭环）：依赖 PH-JM-01；退出条件 TASK-003～005 的进程、报告、调度和目录集成通过，无真实业务发压。

PH-JM-03（包装与实际资格）：依赖 PH-JM-02；退出条件 TASK-006/007 包结构、宿主桥接、真实 CLI/report 与汇总通过，所有 AC 有证据，TQ-001～004逐项结案。

| 任务 / 依赖 | 实施步骤与独立交付 | 针对性验证（候选包目录运行） | 回退边界 |
| --- | --- | --- | --- |
| TASK-001 / 无 | 定义契约及数值单位；实现纯粗细测函数；写独立输入输出用例。只写 contracts.py、search.py、tests/test_search.py、tests/__init__.py。 | Python `-m unittest tests.test_search -v`；固定四轮粗测、3%下降阈值两侧、预设末档、零 TPS、中点、同组中心、先左、并列、失败边界、六轮上限、无复测 | 保留失败证据；只修当前四文件，不碰运行层 |
| TASK-002 / 001 | 定义 JMX 结构身份；读取属性名而非只识别 stringProp；实现副本及独立语义差异验证；检查相对依赖和不可隔离节点。写 jmx.py、preflight.py、tests/test_jmx.py。 | Python `-m unittest tests.test_jmx -v`；intProp/stringProp、注释/PI、表达式拒绝、禁改字段、A→B 前置两分支、未知可执行节点 | 原件始终只读；不通过改 URL、时长、线程组 enabled 修输入 |
| TASK-003 / 001 | 定义版本化官方字段；读取 report 目标行及显示时间；加入同轮只读核验。写 report.py、audit.py、tests/test_report.py，维护 report-fields.md。 | Python `-m unittest tests.test_report -v`；非默认百分位、Total/前置排除、计数差异仍按 report、标签冲突及不可读 | 不自算 P90 替代，不改 report/JTL；版本不符阻止伪造观察 |
| TASK-004 / 001、002 | 实现存储和官方进程适配；无网络探针验证参数传递与真实等待。写 process.py、storage.py、tests/test_process.py、tests/test_storage.py。 | Python `-m unittest tests.test_process tests.test_storage -v`；中文空格元字符、非覆盖、spawn失败与启动后失败分离、进程尚活跃不放槽 | 不终止未知进程、不覆盖结果、不自动再发压；资格不通过则记录 TQ-002 |
| TASK-005 / 001～004 | 实现单进程调度、冻结确认配置、逐目标隔离、持久问题队列、六列汇总；写 controller.py、host.py、summary.py、runner.py、tests/test_controller.py。 | Python `-m unittest tests.test_controller -v`；模拟 CLI 的确定性闭环、切换/质量停止、核验差异继续、共享故障、未知在途不重放 | 停止新轮，保留已启动与未知状态；只有汇总可单独重渲染 |
| TASK-006 / 005 | 编写 Skill/元数据及配置、支持范围引用；实际宿主问题卡联调。写 SKILL.md、agents/openai.yaml、references 及 tests/test_entry.py。 | Python `-m unittest tests.test_entry -v`；create-skill 结构验证、秘密扫描、真实提示前向测试；问题卡投递/展示与后台继续证据 | 工作区候选，不全局安装；卡片未证实不能标通过 |
| TASK-007 / 006＋任务确认 | 使用用户本次 JMX、现有 JMeter/Java 和固定控制器真实执行；核验独立报告及汇总。仅产生报告和验证证据，不临时改算法。 | 按 test-plan 第4节；独立核对 CLI、每轮 HTTP 集合、原件 SHA、report 所有列与最大合格 TPS | 不因缺少覆盖追加业务轮；真实未触发分支用离线证据，不伪称实际触发 |

上述任务表保留实施依赖、针对性验证和回退约定，属于可复核的任务规范；不是尚待执行清单。命令使用已有Python3.11，从Skill目录执行。后续只按变更影响运行相关模块，禁止为了文档回顾重发业务请求。

## 4. 已完成的阶段与证据

| 任务 | 实际完成与验收 | 证据 |
| --- | --- | --- |
| TASK-001 | 66项模块测试、16项独立检查；固定寻峰与精度边界 | DEV-E01 |
| TASK-002 | 初次29项模块、17项独立检查；后续相关回归覆盖最终预检 | DEV-E02、DEV-E04 |
| TASK-003 | 官方5.6.3报告读取及只读核验；后续精度/过滤说明修订 | DEV-E03、DEV-E04 |
| TASK-004 | Windows实际argv探针、串行等待、独占存储 | DEV-E03 |
| TASK-005 | 控制器、失败分流、六轮预算与汇总 | DEV-E03、DEV-E04、DEV-E05 |
| TASK-006 | Skill验证P0/P1为0、固定入口、宿主真实问题卡 | DEV-E06、DEV-E07、DEV-E08 |
| TASK-007 | 三目标共6轮，原件不变、逐轮XML及官方字段/时间、决策回放通过 | DEV-E05 |

PH-JM-01～03实现与限定环境验证已结束。实际任务范围50～500、预设50/100/200/500、120秒/轮、错误率≤0.5%、P90≤2500ms已由用户确认。真实轮数为1/4/1，正常停止不强行用满。用户输入、地址和原始报告仅本地留存，不成为公开默认配置。

## 5. 交付及剩余边界

验收矩阵及coverage-v1.1.json关联18项FR、24项BR、6项NFR、26项AC；软件运行链通过与接口是否质量合格分别记录。正常不复测、有限搜索与report优先仍是用户明确的取舍。

当前仅支持架构所列适配边界。没有自动同目录副本布局、非10倍数上下限自动对齐、全平台通知或全局安装。真实任务初轮超标的请求结束并提示，用户要求记录问题并交付，没有后续补测授权。

## 6. 文档回顾与发布任务

本次为documentation-only路线，由Codex执行。逐份核对主文档、Skill引用、RTM、TQ和验收记录；原始失败、旧基线和旧清单只读保留。新版本先建立语义差异处理记录，再核对源码哈希、敏感信息及链接，生成新发布清单，按本次用户指令推送已核实仓库。具体发布状态以独立推送回执为准，文档写好不等于远端已更新。

先前landed-review的同哈希检查只证明基线未变，不能作为本次内容回顾结论；它由新的reconciliation-review.md和独立检查回执补正，不改写原记录。
