# WorkBuddy 宿主操作与兼容范围

## 候选状态和导入

本版本复用原12个业务核心，新增完整性、监督运行和状态/回执适配。它是待人工验收的工作区候选，不是已验证的正式发行版。探针 M01 已证实 UI 导入会增加 `_user_meta.json`；本实现只豁免该根目录普通文件，不使用其内容作为指令或配置，不豁免其他代码/缓存。使用 -B 避免产生额外 pyc。

后续正式候选通过官方技能 UI 导入，实际安装根从 Skill 调用获取，不硬编码 `.workbuddy` 或作者路径。同名旧版先备份并处理冲突，不静默覆盖；内置技能目录不可写。停用只影响技能可用性，不等于停止已启动任务。卸载/升级不要删除历史报告。

首期目标环境：Windows、现有 Python3.11+标准库、Java及JMeter5.6.3；WorkBuddy5.5.6 Agent/Git Bash 是已有探针环境。自然语言触发、停用、第二环境尚未完成资格验证。其他版本/模式需人工补验，不由命令名猜兼容。

## 固定入口

用已确认 Python 加 `-B`，后接已安装根的 `scripts/workbuddy_bridge.py` 绝对路径。路径作为独立参数并按实际 shell 引用；不把用户文本拼成 shell 代码。不要假定 PowerShell 工具或所有 Git Bash 命令都存在。

| 子命令 | 参数 | 含义 |
|---|---|---|
| verify | 无 | 只读 SHA 与路径核对；非数字签名、不证明宿主资格 |
| prepare | --source 本次JMX | 只读结构识别，不发压 |
| run | --config 本地配置 | 一次监督启动，须由实际宿主后台工具承载 |
| bind-task | --output 目录 --task-id 真实ID --receipt 真实回执 | 关联宿主 ID；不会启动、停止或证明进程退出 |
| status | --output 目录 | 核心及报告的保守状态投影 |
| questions | --output 目录 | 未答条目、已答计数、不可读条目 |
| acknowledge | --output 目录 --id ID --receipt 回执 [--response 答复] | 真实回执与答复关联；不修改运行计划 |

入口不会自动调用 WorkBuddy 工具，Skill 要使用本会话实际工具。后台受理一次 run 后保存 task ID；未知时禁止重新 run。TaskCreate 一类任务清单只是展示，不驱动发压。

相对配置路径按配置 JSON 所在目录解析并保存到 host/confirmed-config.json，不修改原配置。输出必须全新、在技能目录外；重复目录不是可自动清理的错误。缺确认、预检失败或包校验失败均不启动子进程。

## 生命周期与证据

监督入口为固定 Python runner 子进程创建 host/runtime 工作目录，避免 JMeter 版本查询污染安装目录。核心输出仍为 HTTP名称/并发/report、result、plans。host/launch.json 在 spawn 前记录意图，再记录 child PID；host/exit.json 仅在实际 wait 返回后记录退出码。controller-console.txt 保留原字节，不将 GBK 硬编码为所有 Windows 日志的解码契约，评分使用官方 JSON。

宿主可能同时终止监督器与子进程，来不及落 exit。此时状态是 running-or-unknown，不自动推定仍在运行或已经停止。PID 可能复用，PID及记录时间不是 OS 创建时间证明；现场观察须关联准确创建时间、父子关系和任务路径。

status 区分 unknown、running-or-unknown、controller-exited-unsuccessfully、incomplete、completed、completed-with-technical-issues；后两者只有产物一致时 ready_for_report=true。技术问题终态必须披露，不声称所有接口成功。status 不证明任意 Java 子孙已退出，不替代停止实验。

读取阶段复核官方 report、已记录 SHA、轮次、质量判断与峰值；发现 report 被改动不自动修正值或重发。运行中的原算法与审计策略不变。

## 提问与延迟通知

控制器产生问题就继续下一个目标，提问由宿主处理。工具阻塞模型时，用户答复之前允许后续弹窗和完成提示延迟；文件与后台仍可推进。答复后重新读取队列，不把已完成报告当作问题已处理。

submitted-to-host 核对原卡片，不重发。answered 重复同一回执/答复是幂等，不同内容或倒退拒绝。host/question-events.jsonl 区分 intent/committed；recorded_at 是记录时间，displayed_at/answered_at 没有独立证据时为 null。回执字符串是宿主声明，不能认证真实UI行为。

host/ack.lock 串行化写入；遗留锁表示提交可能不完整，不自动删除或重复答复，先核对原问题及真实工具记录。程序不负责弹窗、不伪造用户回答。

## 人工验收仍需补齐

1. 候选正式导入后 verify，新会话自然语言触发、显式调用和停用。
2. M02 补实际问题展示/答复时间；不能用入队时间代替等待区间。
3. M03c 补真实 task 停止回执、进程身份及前后观察；截断 JTL/无 report 只支持中断现象。
4. 第二独立用户/机器。本机新会话不算第二环境。

先补已有证据再决定是否需要新实验，缺文件不自动重跑。两次错过停止窗口不证明人工停止功能应取消，只披露交互耗时限制。
