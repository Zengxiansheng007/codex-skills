> 公开投影：业务规则与原编号保留；“本轮”指源文档编写阶段。源哈希、路径适配与当前发布范围见 jmeter/docs/publication-context.md 及导出清单。

# 改动范围与开发顺序 v0.1

日期：2026-10-13。状态：未来实现写集；本轮没有执行这些修改。主规格的 Implementation Decisions 保留模块/接口语义，本文件记录准确候选位置，避免把事实路径写成永久接口。

## 当前候选基线

目录：runner 候选（历史本地参考，未随本次导出）。仅此候选已读取，不能代表 WorkBuddy 安装版本。

| 文件 | 当前 SHA256 |
|---|---|
| scripts/jmx.py | 837B954902C11D49F88C92CCC65CFFC20D9965A2C93B6298BDB57C6B3D89F524 |
| scripts/preflight.py | 663EAF8C86D70F932BAD7EC64E6864F75D1CBD9D94430AA8D54FF8A3032861B1 |
| scripts/controller.py | BADC38AE66DDFDDE39FC3913A17824F1BB0F67DB50ACB7517F5C8262E305BB54 |
| scripts/runner.py | FCC605E1525BF4F20BBB2127B5DEFAF2FADFC23A586C6222C07B9FA9F1EAD928 |
| scripts/workbuddy_bridge.py | 7B0AA883C0CF47FB77B445E0A1DEAE357FA98DE942B6B267AC289C844A6E42CF |
| scripts/storage.py（拟保留） | AB0968D64DF26FFE48CBBD42FB3FB16E55CDF5C7F481D366E798E781AF206232 |

进入开发前刷新准确基线并查看用户已有变更，不覆盖或改写历史候选证据。本次没有把候选复制到安装目录。

## writer：新增范围

未来候选为独立 jmeter-tps-writer 包，不写进已安装 Skill。以下文件名是实现建议，不宣称已创建。

| 模块 / 资源 | 拟责任 | 对应需求 |
|---|---|---|
| SKILL.md、使用参考 | WorkBuddy 调用顺序、必要补问、固定入口、默认断言、失败停止、分层交付 | REQ-001–006 |
| task_contracts | 数据结构、输入条件、会话选择、来源/授权与版本检查 | REQ-001–006 |
| curl_adapter / 小型 Java helper | 复用 JMeter 5.6.3 解析器，生成规范请求模型，给出保真与不支持差异 | REQ-001 |
| plan_builder | 原生业务组、头、断言、手工/自动认证与稳定角色映射 | REQ-002、003、005 |
| trial_copy | 逐目标副本、1/0/1、单账号 CSV 隔离、独立差异校验 | REQ-004 |
| execution | 官方非 GUI 命令、Windows .bat 参数边界、真实结束与证据 | REQ-003、004 |
| validation / result | 目标覆盖、认证/断言、消费者接收、失败/提醒/未知与总体结论 | REQ-004、006 |
| 固定认证模板 | 附在登录 HTTP 下的初始化 / 收集发布；只写声明生成产物 | REQ-003 |
| 账号/手工 Cookie 模板与格式说明 | 原生 CSV 格式、变量、填写、EOF、共享与会话范围 | REQ-002、003、006 |
| 入口行为测试、受控夹具 | 请求回显、登录、Cookie、断言、依赖及故障证据 | AC-001–006 |

不引入远程 converter、MCP 上传、GUI 插件、Taurus 等重型依赖。Java helper 仅复用用户已有 5.6.3 环境；开发时的构建/分发方式需记录资格，不要求工程师现场编译，也不因规格授权自动安装 JDK。

writer 的短验证执行器参考现有已资格的 .bat 命令边界，保留单字符串 cmd 与 shell=False、中文/空格路径及受限字符行为；不复制 runner 寻峰控制器。是否抽取公共工具应按实际依赖成本判断，不为复用扩大共享模块重构。

## runner：必要改动

| 准确文件 | 当前行为 / 缺口 | 拟最小改变 |
|---|---|---|
| scripts/jmx.py | groups 只认标准 ThreadGroup；普通前置须同组/同 ancestors 且先于目标；复制只保留 target＋prerequisites | 显式认证角色解析与选择。业务 targets 仍只认标准组；保留旧普通前置约束。正式副本使用目标＋必要认证＋普通前置的 HTTP 集合，仍只改目标并发/HTTP enabled。 |
| scripts/preflight.py | SAFE 没有 setUp 或 JSR223；现成文件、变量、相对布局规则保守 | 增加经过契约核对的 SetupThreadGroup 与确切固定前/后处理资格；增加限定生成依赖绑定。其他任意脚本、动态/相对文件和 unsupported 保持原规则。 |
| scripts/controller.py | 所有目标在启动前预检；每轮执行后直接读取目标官方指标 | 配置增加可选认证描述与目标关联；执行前传入同一消费契约，结束后先核认证证据及登录样本，再进既有目标指标/技术故障路径。预算、算法和后续目标策略不改。 |
| scripts/runner.py | prepare 输出全部 HTTP/标准组；没有公开只读接收检查 | 保留旧输出字段，新增明确业务候选/认证角色与协议能力；增加 check-input 无发压入口。不调用正式 run 验短脚本。 |
| scripts/workbuddy_bridge.py | load_confirmed 自己调用旧 preflight；结束核验读取原始轮次 | 传递相同可选认证契约，避免桥接仍在旧门拒绝。完成核验按需读取本轮认证证据；宿主绑定、后台监督、等待/提问/停止机制保持。 |
| scripts/authentication.py（拟新增） | 当前没有认证描述/产物的限定解释器 | 集中实现 AuthContract 绑定、生成依赖解析及本轮 AuthenticationResult 核验，供预检、控制器与宿主结束核验复用。不是正式调度器。 |
| references/task-config.md、supported-inputs.md | 没有认证协议与固定生成依赖的范围 | 更新可选字段、旧计划兼容、资格/拒绝条件与每次正式确认边界。 |
| SKILL.md / MANIFEST.json | 新接口、源码或资源进入包时需一致 | 只在候选验证完成后同步说明与重建文件清单；不靠修改 manifest 宣称 runtime 通过。 |

协议参数应走公共接收路径，不能在控制器、桥接和 writer 各造不一致的认证判断。jmx 的旧标准组含义保持；识别 setUp 不意味着它自动成为业务目标。源 hash、结构身份和消费者版本都要绑定。

### 保留模块

- scripts/search.py 与 scripts/contracts.py 的寻峰数据模型、数值单位、6 / 4 轮预算与 3% 决策。
- scripts/process.py 的正式官方命令、版本探针、启动/结束观察与 Windows 参数边界。
- scripts/report.py 的目标行、P90/TPS/错误率、官方起止时间读取。
- scripts/summary.py 的既有峰值评分与汇总；认证错误通过现有技术问题结果说明，若现有结构能表达，不另改版式。
- scripts/storage.py 的现有任务/轮次布局与事件机制。新增认证产物按当前 plan 名在已有布局派生，不能假设每轮已经有独立 plans 子目录。
- 既有问题队列、WorkBuddy 等待/结束提示及宿主中断语义。

若实际发现这些模块有与本次认证接口直接相关的必需调整，先写清根因/影响和增量测试，再修订写集；不顺带全仓重构。

## 开发先后与技术资格门

这不是执行台账，也未启动票或消耗开发额度。

1. **G-01 生成资格**：本机 5.6.3 无头解析/序列化、支持 cURL 语法与字面表达式保真。先用合成材料证明，不发送真实秘密到外部工具。
2. **G-02 原生运行资格**：认证前/后处理顺序、N→1 验证隔离、CSV 原生读取、属性/目录解析、完整发布和失败不发依赖业务。尤其证明无关线程组不打开错误生成引用、不执行未选登录。
3. **writer 编写**：实现新输入和原生生成，已有计划仅检查；默认头/断言、手工路径先形成可核产物。
4. **writer 短验证**：副本契约、官方单次执行、分层结果与失败停止。旧缺断言提醒按真实例外落地。
5. **runner 最小适配**：统一认证消费契约、精确 HTTP 集合、公开 check-input、本轮证据与桥接传递。
6. **关联回归 / 集成**：按用户确认的入口边界核对；最后用经过授权的 loopback 真 JMeter 和 WorkBuddy 验证实际链路。
7. **后续交付**：候选文档回顾、包完整性和使用说明；安装/发布/远程 Issue 另按具体目标授权。

G-02 不通过时，自动认证消费者不可标就绪。不得为绕过失败而放开任意动态路径、修改正式脚本文本/CSV 引用或自动改线程组 enabled；应在允许边界内修订生成结构，否则报告需要范围决策。

## 本轮写集

本轮只新增本规格目录的文档，保留需求 v1.1、历史草稿、原型、runner 候选和正式 Skill；不调整 grill-context 或其他流程状态。

