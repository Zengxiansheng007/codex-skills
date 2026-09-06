---
artifact:
  id: ART-GRILL-TEST-PUBLIC-001
  type: test-plan
  version: 1.0.0
  statusCode: approved
  statusLabelZh: 已批准
  owner: qa
  sourceBaseline:
    codeCommit: b4fa50611f2f4c627903df2cc439ff483ce6cfc6
  approvalBasis: reviewed-document publication requested by user; approved product
    rules unchanged
---
# 测试计划及实际结果 v1.0

本文件区分计划、准备检查、已执行测试和主机能力限制。当前代码测试和发布验证已执行；原v0.1“产品测试未执行”的状态仅属于当时的规划快照。

## 实际计数

| 组别 | 结果 |
| --- | --- |
| test_validate_grill_report.py | 14个测试函数通过 |
| test_grill_phase_contract.py | 17个测试函数通过 |
| test_grill_artifact_checks.py | 3个函数调用；路径与实际目录联接断言通过，文件符号链接分支因主机权限提前返回 |
| 独立公共CLI QA | 16个场景通过，1个文件符号链接场景因同一主机能力限制跳过 |
| 路径专项 | 版本替代、越界路径及真实Windows目录联接验证通过 |
| 四个Skill结构及变更记录 | 均通过 |
| 安装后验证 | 8项检查通过，包括全局测试、结构和记录状态复核 |

34是观测到的具名函数调用数，三个测试脚本均以成功状态退出；其中一个函数在记录主机能力跳过后提前返回。这不是测试框架逐函数PASS/SKIP计数，也不是“34项全部实测通过”。43项检查属于早期需求文档一致性检查；80项属于开发准备，均不能充当产品测试数。“13个AC已验证”也不等于只有13个测试。

## 风险覆盖

关闭依据与P0双源检查、旧报告无写权限、普通台账与正式写入门槛分离、例外消费/完成、暂停/恢复/重开、冻结计划、真实后置哈希、重复批次、部分失败、no-op、绝对/相对路径、版本替代和reparse点均有相应验证。

独立QA先建立正常路径再构造负例，避免把无关前置失败当成目标保护有效。原生Agent前向测试验证了：
- 单题回答只积累评审状态，正式PRD未变；
- 整场关闭后集中合并，报告与台账一致，无重复回写审批；
- 活跃Grill中的领域建模保留正式词汇表，独立调用正常更新。

## 公开可复验入口

从仓库根执行，前提是可用Python环境已具备jsonschema：

~~~text
python -B skills/grill-system/scripts/test_validate_grill_report.py
python -B skills/grill-system/scripts/test_grill_phase_contract.py
python -B skills/grill-system/scripts/test_grill_artifact_checks.py
~~~

若环境已安装create-skill，可使用它的结构/变更记录校验器；它是显式的可选安装工具，不是这四个Skill的打包依赖，也不得自动安装。

[证据摘要](evidence-summary.json)给出实际函数名、场景和原始证据哈希。额外QA及前向用例摘要来自本次实际运行，原始私有任务日志未公开；不要把摘要误认为完整公开测试harness。

## 限制

测试主机不能创建文件符号链接（WinError1314），没有提权或改ACL。真实目录联接通过后，仍不宣称所有链接类型、平台或未来Agent行为均已穷尽验证。首尾哈希不能证明中间没有写后恢复；局部流程检查不能取代全局工具拦截。

