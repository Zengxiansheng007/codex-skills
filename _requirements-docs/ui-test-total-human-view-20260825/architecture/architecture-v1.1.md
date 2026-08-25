# UI-Test 产品级总 Human View 架构方案 v1.1

## 文档状态

- 状态：候选架构已完成，待落地审查
- 需求锚点：`RA-UI-TEST-TOTAL-HUMAN-VIEW-20260825-v1.1`
- 参考方案：`research-total-human-view-20260824/reference-solution-adaptation-v1.0.md`
- 实现边界：仅当前候选工作区；不代表正式 D 盘发布

## 1. 架构目标

在既有 `Source Case -> Case IR -> 多投影` 管线之上，增加受治理的 Display Registry 和产品聚合投影：

```text
Source Case + project config + Public Flow Registry
    -> Schema + semantic validator
    -> Case IR (Stable ID + display_name + precondition_group)
    -> per-case Human/Midscene/Resolved/Playwright
    -> product aggregate renderer
       -> Markdown Human View + outline JSON
    -> JCS hashes + manifest + drift gate
```

Source Case 继续是业务事实唯一来源；项目配置/Registry 只提供受治理的显示名和公共 Flow 定义；Renderer 不猜测业务名称、不手工补写事实。

## 2. 产品级节点模型

产品级 outline 固定为：

```text
项目组
  产品显示名
    系统显示名
      模块显示名...
        功能显示名
          公共前置操作
          中文用例名
            特殊前置操作（有事实时才生成）
            操作
            断言
```

产品和系统使用独立 Stable ID 与 `source_ref`。当前两者显示名都为“运维管理系统”，必须保留两个节点，不做同名去重，也不新增重复校验。

## 3. 组件边界

| 组件 | 输入 | 输出 | 失败语义 |
|---|---|---|---|
| Project/Display Registry | project config、显示名映射 | 产品、系统、模块、功能显示名 | 缺失或冲突的受治理映射阻断 |
| Source Case Validator | Source Case | Schema/semantic issue list | P0/P1 阻断 lowering |
| Case Lowerer | 合法 Source Case | Case IR、source hash | 缺 display_name/precondition_group 阻断 |
| Public Flow Resolver | Flow Registry 引用 | Flow 版本、hash、步骤 | 缺版本/冲突阻断聚合 |
| Per-case Compiler | Case IR + dependency graph | 独立 Human/Midscene/Resolved/Playwright | 保留完整 setup，保证单例可运行 |
| Product Aggregate Renderer | `in_sync` Case IR 集合 | 总 Human View + outline JSON + manifest | stale、drift、scope 或公共 Flow 冲突阻断 |
| Drift Gate | source/dependency/output hashes | `in_sync`、`dependency_stale`、`manual_drift` | 非 in_sync 不得发布 |

## 4. 关键契约

- Source Case 必须有 `display_name`、`precondition_group`、`special_preconditions`。
- Case IR 保留 `display_name`、`precondition_group`，特殊前置进入 `normalized_steps.section = special_preconditions`。
- 产品聚合必须从 Registry 解析项目组、产品、系统、模块、功能显示名；缺失时 fail-closed，不回退 Stable ID。
- 同一功能同一 `precondition_group` 只生成一份公共前置；同组步骤不同则报 `E_COMMON_PRECONDITION_CONFLICT`。
- 产品聚合只在功能节点下渲染公共前置；单用例输出仍完整保留 setup。
- 每个操作固定生成 `参数/数据` 节点，每个参数生成独立原子节点；禁止 `<br>` 事实拼接。
- 所有可见节点使用显示名，`stable_id`、`node_id`、`source_ref`、manifest 使用机器标识。

## 5. 关键 ADR

### ADR-THV-001：复用现有 IR 管线

采用现有 compiler/contracts/manifest，避免引入第二套用例运行时。收益是迁移成本低、既有语义校验和 JCS 可复用；代价是必须扩展旧 Case IR Schema。

### ADR-THV-002：公共前置按显式 Flow Group 去重

用 `precondition_group` 和 Flow Registry 版本做去重键，不按文本相似度合并。收益是治理可追溯；代价是不同流程必须显式注册。

### ADR-THV-003：产品/系统同名仍保留两层

产品与系统语义实体不同，名称相同不代表可合并。通过 Stable ID 区分，Human View/XMind 保留双层，避免丢失系统边界。

### ADR-THV-004：派生物状态先失效后重编译

显示名、公共 Flow 或 Source Case 改变时先置 `dependency_stale`；人工改派生物置 `manual_drift`；只有全量校验通过才能恢复 `in_sync`。

## 6. 质量属性与验证

| 属性 | 机制 | 验证 |
|---|---|---|
| 确定性 | JCS、稳定排序、显式 Registry | 双次编译 hash 相同 |
| 语义完整性 | Rule Registry + 负例 | A/B 变体和错误断言阻断 |
| 可维护性 | 公共 Flow 单一事实、Page/Flow 依赖 digest | 公共 Flow 变化反向标 stale |
| 可追溯 | Stable ID、node_id、source_ref、lineage | 节点回溯检查 |
| 可扩展 | Registry 驱动模块路径和显示名 | 新模块只增加配置/Source Case |
| 安全 | D 盘路径规则、敏感扫描 | 扫描 0 命中 |

## 7. 风险与边界

- XMind 桌面 Golden 仍是外部应用验证门禁，尚未在本轮自动完成。
- 当前实现只覆盖候选工作区，不自动写入 `D:\UI-Test` 或 `D:\RAG`。
- 不执行天津私有 UI、不执行生产或业务写操作。
