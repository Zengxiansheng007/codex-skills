# JMeter TPS Runner：需求、实现与验证

固定程序执行用户已有JMX，逐HTTP请求在确认范围和六轮预算内寻找最高合格已测TPS。仅修改运行副本的线程组并发和HTTP enabled，采用官方report数据。

| 文档 | 当前版本与用途 |
| --- | --- |
| [PRD](prd-v1.3.md) | v1.3；保留已批准需求条款，更新交付事实 |
| [架构](architecture-v1.3.md) | v1.3；组件、接口、目录、实际能力及限制 |
| [开发计划](development-plan-v1.2.md) | v1.2；任务、实际执行路线及验收 |
| [测试计划](test-plan-v1.2.md) | v1.2；风险覆盖、既有结果及证据边界 |
| [回顾差异](reconciliation-review.md) | 逐项处理及仍有限制 |
| [需求追踪](coverage-v1.1.json) | FR/BR/NFR→AC→任务→证据 |
| [验收矩阵](acceptance-matrix-v1.1.json) | 26项AC |
| [技术资格](technical-qualifications-v1.1.json) | TQ-001～004，限定环境 |
| [证据索引](evidence-index.json) | 脱敏摘要与原记录SHA；原始业务材料本地保留 |
| [历史基线](baseline-manifest.json) | 原版本指纹，历史不覆盖 |
| [实现清单](implementation-manifest.json) | 25个发布源码文件及SHA |

使用入口见[Skill](../../skills/jmeter-tps-runner/SKILL.md)，配置及限制见其references目录。依赖现有Python3.11、Windows Java和JMeter5.6.3。

首次123项集成、最终52项关联回归通过（有重叠，不相加），另有寻峰16项及XML17项独立检查。真实授权验证完成三个请求共6轮；执行正确不等于所有接口达到质量门槛。

当前上下限均须10的倍数，运行副本使用输出目录，未支持相对依赖搬移；异步卡片由当前宿主投递。六轮不保证全局最优。文档为Codex已回顾候选，不继承旧版用户批准或自动成为RC。

公开包不含用户JMX、JTL/report、响应体、实际任务配置、日志、凭据或本机路径；本次仅GitHub，不全局安装、不同步GitBook。
