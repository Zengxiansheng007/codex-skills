# UI-Test Human View 展示名与公共前置操作需求 v1.1

> 状态：需求评审已确认
>
> 本版本记录已确认的产品/系统双层展示、中文显示名、公共前置 Flow、特殊前置和派生物漂移治理要求。它仍是需求文档，不包含架构选型、实现代码或正式资产迁移结果。

## 1. 需求背景

当前 UI-Test 资产同时使用稳定英文 ID 和中文业务名称，但产品级 Human View/XMind 总用例在部分节点直接显示稳定 ID，例如 `operations-config`、`announcement-management` 和 `BOPS-ANNOUNCEMENT-P0-A`。同时，登录、进入运营配置、进入消息管理、进入公告管理和点击创建等公共流程仍然跟随每条 Source Case 的 setup 重复出现，导致总用例层级不利于阅读、维护和长期治理。

本需求只改变展示与用例组织方式，不改变稳定 ID、路径治理、Source Case 唯一事实源、风险等级和 UI 写操作边界。

## 2. 目标与非目标

### 2.1 目标

1. Human View 中的模块路径、功能名称和用例名称显示中文业务名称。
2. 稳定英文 ID 继续用于目录、引用、依赖、哈希、manifest、Source Case lineage 和机器接口。
3. 产品级 XMind 总用例在功能节点下，把公共前置操作与具体用例作为同级节点展示。
4. 具体用例仅展示自己的特殊前置操作；没有特殊前置操作时不生成空节点。
5. 每条用例仍可单独编译、单独运行 Playwright，并通过引用复用公共前置流程。
6. 中文名称、公共前置操作和特殊前置操作全部由 Source Case/项目配置/公共 Flow Registry 编译生成，禁止人工修改派生 Human View。

### 2.2 非目标

- 不修改稳定路径中的英文目录 ID。
- 不修改登录凭据存储方式和测试环境边界。
- 不把公共前置操作变成只能依赖其他用例执行的隐式状态；每条独立用例仍必须能够完整执行。
- 不改变 R2 仅允许可见 UI 写操作、每次 run 最多一次提交及不清理测试数据等既有规则。
- 不在本需求中扩展产品级测试覆盖范围。

## 3. 术语和事实来源

| 术语 | 定义 |
| --- | --- |
| Stable ID | 机器治理用稳定标识，例如 `operations-config`、`announcement-management`、`BOPS-ANNOUNCEMENT-P0-A`。 |
| Display Name | 面向人和 XMind 的业务显示名称，例如“运营配置”“公告管理”“创建系统公告核心冒烟”。 |
| 公共前置操作 | 在同一产品/系统/模块/功能下，所有或一组用例进入待测功能前都需要执行的固定流程。当前试点为登录并通过完整菜单进入公告创建页。 |
| 特殊前置操作 | 仅某个用例或分支需要的额外准备步骤，例如特定权限、特定列表状态或特定环境数据。 |
| Source Case | 单条自动化功能测试用例的唯一业务事实源。 |
| Public Precondition Flow | 可版本化、可复用、可单独校验的公共前置 Flow 资产。 |

事实来源优先级固定为：

1. Source Case 中的用例事实和特殊前置事实；
2. 项目配置中的产品、系统、模块、功能 Display Name 映射；
3. Public Precondition Flow Registry 中的公共流程定义；
4. Compiler 只负责 lowering 和投影，不得自行猜测中文名称或补写业务事实。

## 4. 功能需求

### FR-DISPLAY-001 模块路径中文展示

项目配置必须为每个可出现在 Human View 的稳定模块 ID提供中文 Display Name 映射。当前试点至少包括：

| Stable ID | Human View 显示名 |
| --- | --- |
| `operations-config` | `运营配置` |
| `message-management` | `消息管理` |
| `announcement-management` | `公告管理` |
| `create` | `创建` |

要求：

- Human View、产品级总 Human View 和 XMind outline 的节点标签使用 Display Name。
- 目录路径、Source Case scope、依赖引用、node_id、source_ref 和 manifest 继续使用 Stable ID。
- 显示映射必须来源于项目配置或受治理 Registry，不能硬编码在 renderer 中。
- Stable ID缺少 Display Name、映射重复或同一 scope 映射冲突时，编译和聚合必须 fail-closed。
- 其他未覆盖模块可以继续使用英文 Stable ID存储，但不能静默伪装成中文名称；应明确标记为 `display_name_missing` 并阻断正式 Human View 发布。

### FR-DISPLAY-002 用例中文展示

每条 Source Case 必须具有独立的中文 `display_name`，用于 Human View 和 XMind 的用例节点。当前试点建议使用：

| Case ID | 中文用例名 |
| --- | --- |
| `BOPS-ANNOUNCEMENT-P0-A` | `创建系统公告核心冒烟` |
| `BOPS-ANNOUNCEMENT-P0-B` | `创建首页弹窗公告核心冒烟` |

要求：

- Human View 标题和 XMind 用例节点显示 `display_name`。
- `case_id` 仍必须作为机器字段、source_ref 或“用例编号”信息保留，不能被中文名称替代。
- `display_name` 为空、含稳定 ID代替中文名称、同一 scope 下重复或与分支事实冲突时阻断编译。
- Human View 可以在中文标题下保留“用例编号：BOPS-...”机器可追溯信息，但不得把英文 ID作为主要用例名称。
- `title` 的历史字段必须定义迁移规则：旧资产中若 `display_name` 缺失，可在迁移阶段由已确认的 `title` 生成候选；候选必须通过中文显示名语义校验后才能发布。

### FR-PRE-001 公共前置操作与用例同级

产品级总 Human View 在功能节点下固定采用以下结构：

```text
产品显示名
  模块显示名
    功能显示名
      公共前置操作
        操作
          参数/数据
            原子参数
          预期结果
      用例中文显示名 A
        特殊前置操作（仅有时生成）
          操作
            参数/数据
              原子参数
            预期结果
        操作
          参数/数据
            原子参数
          预期结果
        断言
          操作
            参数/数据
              原子参数
            预期结果
      用例中文显示名 B
        ...
```

要求：

- `公共前置操作` 与具体用例节点是同一 `功能` 节点下的兄弟节点。
- 同一功能下多个用例引用相同公共 Flow 时，总用例只渲染一份公共前置操作，禁止按用例重复展开。
- 公共 Flow 的步骤顺序、参数、预期结果和 evidence 要求必须来自 Flow Registry。
- 公共 Flow 变更后，依赖该 Flow 的所有用例必须被标记为 `dependency_stale`，不得继续生成 `in_sync` 派生物。
- 若同一功能存在多个公共前置 Flow 变体，必须按显式 `precondition_group` 或 `flow_id` 分组，不得自动合并语义不同的流程。

### FR-PRE-002 特殊前置操作单独归属用例

Source Case 增加或规范化 `special_preconditions` 字段，用于声明当前用例独有的前置步骤。

- `special_preconditions` 非空时，在该用例节点下生成“特殊前置操作”节点。
- `special_preconditions` 为空或不存在时，不生成空的“特殊前置操作”节点。
- 特殊前置操作不得被提升为公共前置操作，除非用户确认并完成 Flow Registry 变更。
- 特殊前置操作必须支持参数、预期结果、风险、证据、binding_ref 和 lineage。
- 当前 A/B 试点没有额外特殊前置操作时，两个用例均不生成“特殊前置操作”节点。

### FR-PRE-003 独立执行兼容

公共前置操作在总用例中只展示一次，但每个单独的 Human View、Resolved Case 和 Playwright Test 必须展开或引用足以独立执行的公共 Flow。

- 单独运行用例时仍执行登录和进入待测功能页面的完整公共流程。
- 产品总用例只负责治理视图去重，不得改变单用例运行语义。
- Midscene View 使用公共 Flow 引用，不重复探索已稳定的公共模块进入步骤。
- Playwright Test 通过统一 Page/Flow 对象调用公共前置流程，禁止每个脚本复制菜单定位逻辑。

### FR-PRE-004 前置操作分类语义

编译器必须区分以下三类内容：

| 类型 | Source/Registry 归属 | 总用例位置 | 单用例位置 |
| --- | --- | --- | --- |
| 公共前置操作 | Public Precondition Flow Registry | 功能节点下，与用例同级 | 用例的可执行前置引用或展开 |
| 特殊前置操作 | Source Case `special_preconditions` | 对应中文用例节点下 | 用例的特殊前置区 |
| 被测功能操作 | Source Case `steps.feature` | 对应中文用例节点下 | 操作区 |

禁止把公共前置操作混入被测功能操作，也禁止把特殊前置操作误标成公共流程。

## 5. 数据模型与接口要求

### 5.1 Project Config

项目配置增加受治理的显示名映射：

```yaml
product:
  product_id: ops-platform
  display_name: 运维管理系统

systems:
  - system_id: bops-ops-platform
    display_name: 运维管理系统

display_names:
  module_path:
    operations-config: 运营配置
    message-management: 消息管理
    announcement-management: 公告管理
  functions:
    create: 创建
```

### 5.2 Source Case

Source Case 增加或规范化：

```json
{
  "display_name": "创建系统公告核心冒烟",
  "precondition_group": "announcement-create-common",
  "special_preconditions": []
}
```

现有 `precondition_flow_refs` 保留，用于公共 Flow 的稳定引用；迁移后不得让每条用例自行复制公共 Flow 内容作为第二事实源。

### 5.3 Case IR

Case IR 必须保留：

- `case_id` 和 `display_name`；
- scope Stable ID 与对应 display path；
- `precondition_group`、公共 Flow lineage；
- `special_preconditions`；
- Source Case hash、dependency digest 和 build fingerprint。

### 5.4 Product Outline

outline 节点增加或规范化：

- `display_name` 或等效显示标签字段；
- `stable_id`/`source_ref` 机器追溯字段；
- `node_type = common-preconditions`；
- `node_type = special-preconditions`；
- 既有 `is_unmodified: true` 保持不变。

可见 `label` 使用中文名称；机器字段保留英文 ID，避免 XMind 节点既显示中文又把 ID混入主标题。

产品和系统是两个独立治理字段和两个独立展示节点。当前试点的两者显示名都必须是“运维管理系统”，总用例树必须保留两层：

```text
天津项目组
  运维管理系统        # product.display_name
    运维管理系统      # systems[].display_name
      运营配置
        消息管理
          公告管理
            创建
```

同名不表示同一实体。编译器不得因为产品显示名与系统显示名相同而合并、隐藏或改写任一节点；本需求不新增产品/系统显示名重复校验。产品和系统仍通过各自的 Stable ID、`source_ref`、scope 字段和 lineage 独立追溯。

## 6. 语义校验与门禁

新增以下阻断规则：

- `DISPLAY_NAME_MISSING`：模块、功能或用例缺少显示名。
- `DISPLAY_NAME_NOT_CN`：要求中文的显示名不满足中文业务名称规则。
- `DISPLAY_NAME_DUPLICATE`：仅用于同一实体类型、同一治理范围内会造成无法定位的冲突；不适用于产品显示名与系统显示名相同的合法情况。
- `DISPLAY_NAME_SCOPE_MISMATCH`：显示名映射与 scope Stable ID不一致。
- `COMMON_PRECONDITION_DUPLICATED`：同一功能公共 Flow被重复写入多个 Source Case正文。
- `COMMON_PRECONDITION_MISPLACED`：公共前置操作被编译到具体用例而未进入功能级公共节点。
- `SPECIAL_PRECONDITION_EMPTY_NODE`：没有特殊前置事实却生成空特殊前置节点。
- `SPECIAL_PRECONDITION_PROMOTED`：未批准的特殊前置操作被提升为公共前置操作。
- `PRECONDITION_LINEAGE_MISSING`：公共 Flow缺少版本、hash或 source_ref。

所有 P0/P1 规则必须在 Case IR lowering、单用例渲染和产品聚合三个阶段执行；任何一个阶段失败都不得生成 `in_sync`。

## 6.1 变更、漂移与重新同步治理

显示名映射、产品/系统显示名、公共 Flow 定义、公共 Flow 版本或其引用关系均属于派生物依赖。发生以下任一变化时，编译器必须重新计算依赖状态，不得沿用旧的 `in_sync` 结果：

1. 任何参与 scope 显示路径的 Display Name 发生变化；
2. `flow.login-open-announcement-create` 或其他被引用公共 Flow 的步骤、参数、预期结果、证据要求、版本或 hash 发生变化；
3. Source Case 的 `precondition_flow_refs`、`precondition_group` 或特殊前置事实发生变化；
4. 生成的 Human View、outline、Resolved Case、Midscene View 或 Playwright Test 被人工修改。

处理规则：

- 显示名或公共 Flow 变化使受影响 case 和产品聚合物进入 `dependency_stale`；
- 派生文件人工修改进入 `manual_drift`，不得用重新计算的 hash 掩盖人工修改；
- `dependency_stale` 或 `manual_drift` 不得生成新的 `in_sync` manifest，也不得进入正式产品总用例发布包；
- 重新编译前必须保留变更前备份和 append-only 变更记录；
- 重新编译时重新计算 `source_hash`、`dependency_digest`、`build_fingerprint`、Human View hash、outline hash 及完整 lineage；
- 重新编译后必须依次通过 Schema、语义、显示名、公共前置归属、去重、单用例独立编译、产品聚合、敏感扫描、哈希和 lineage 校验，才可恢复 `in_sync`；
- 缺少中文显示名只阻断对应的正式发布范围，不得用英文 Stable ID 静默回退为中文显示名；未纳入本期覆盖范围的模块可以保留待治理状态。

产品显示名和系统显示名虽然同名，但任一字段变化仍分别触发其自身及下游引用的依赖重算；同名本身不触发错误。

## 7. 验收标准

### AC-DISPLAY-001 中文模块显示

生成的产品总 Human View 中显示“运营配置”“消息管理”“公告管理”“创建”，不显示 `operations-config`、`message-management`、`announcement-management` 作为主节点名称；outline 的 `source_ref` 仍能回溯 Stable ID。

### AC-DISPLAY-002 中文用例显示

总 Human View 中显示“创建系统公告核心冒烟”和“创建首页弹窗公告核心冒烟”；`BOPS-ANNOUNCEMENT-P0-A/B` 仍可通过机器字段定位。

### AC-PRE-001 公共前置同级

在“创建”功能节点下，只出现一个“公共前置操作”节点，并与两个中文用例节点同级；公共登录和完整菜单进入流程不在两个用例节点中重复展开为总用例事实。

### AC-PRE-002 特殊前置按需出现

当前 A/B Source Case 的 `special_preconditions` 为空，因此总用例不生成“特殊前置操作”节点。加入一个仅 A 使用的特殊前置后，只在 A 节点下生成该节点，B 不受影响。

### AC-PRE-003 单用例可执行

单独编译 A 或 B 时，Playwright Test 仍可以通过公共 Flow 登录并进入创建公告页面；总用例去重只影响聚合视图，不影响独立执行。

### AC-GOV-001 漂移阻断

修改显示名映射或公共 Flow 后，相关 case/aggregate 进入 `dependency_stale`；手工修改 Human View 或 outline 后，进入 `manual_drift`，不得被标记为 `in_sync`。

### AC-GOV-002 现有规则不回归

Source Case 唯一事实源、参数原子化、RFC 8785/JCS、敏感扫描、R2 UI-only 和 `is_unmodified: true` 规则全部继续通过。

### AC-GOV-003 产品与系统双层显示

产品级总 Human View 和 XMind outline 均显示两层“运维管理系统”节点，分别对应产品和系统；生成结果不得因名称相同而合并、隐藏或失败。两个节点的机器追溯字段必须分别指向产品 Stable ID 和系统 Stable ID。

### AC-GOV-004 依赖变更后重新同步

修改产品/系统/模块/功能显示名或被引用公共 Flow 后，所有受影响 case 和产品聚合物先进入 `dependency_stale`；人工修改派生物进入 `manual_drift`。只有重新编译并通过完整门禁后，manifest 才能恢复 `in_sync`。

## 8. 当前试点迁移范围

本期只迁移天津项目组运营管理平台的“运营配置 / 消息管理 / 公告管理 / 创建”功能：

1. 为 A/B 增加中文 `display_name`。
2. 在项目配置中补齐模块、功能中文映射。
3. 将 `flow.login-open-announcement-create` 注册为功能级公共前置 Flow。
4. 将 A/B 的重复 setup 转换为公共 Flow 引用；保留单用例独立执行能力。
5. 为 Source Case 增加空的 `special_preconditions` 或按 schema 默认空数组，但聚合器不生成空节点。
6. 重新编译 A/B 和产品总 Human View，执行语义、结构、哈希、敏感和漂移测试。

## 9. 待确认决策

以下决策已确认，作为本版本需求基线：

1. 采用 `display_name` 作为新的明确显示字段，`case_id` 只作为稳定机器 ID和追溯信息，不作为 Human View 主标题。
2. 公共前置操作按“产品 / 系统 / 模块 / 功能”作用域治理；当前公告创建试点落在 `create` 功能作用域。
3. 总 Human View 聚合视图只渲染一次公共前置操作；单用例 Human View、Resolved Case 和 Playwright Test 继续展开或调用该公共 Flow以保证独立执行。
4. 当前 A/B 没有特殊前置操作，因此不生成空的“特殊前置操作”节点。
5. 模块、功能和用例中文显示名缺失时 fail-closed，不回退显示英文 Stable ID。
6. 产品显示名统一为“运维管理系统”；系统显示名独立配置为“运维管理系统”。Human View/XMind 同时保留产品节点和系统节点，不新增产品名与系统名重复校验。
7. 显示名、公共 Flow 和派生物变更采用 `dependency_stale`/`manual_drift` 双状态治理，完成重编译和全量校验后才允许恢复 `in_sync`。

## 10. 评审结论

- 需求评审状态：通过。
- 已确认的 P1 决策：产品/系统双层展示、同名不去重、显示名治理、公共 Flow 依赖失效和派生物重新同步。
- 当前范围：仅天津项目组“运维管理系统 / 运维管理系统 / 运营配置 / 消息管理 / 公告管理 / 创建”试点。
- 下一阶段：先生成新的需求锚点，再由用户确认后进入参考方案检索、架构设计、开发计划和测试计划。
- 本版本不授权正式资产迁移、D 盘写入、全局 Skill 修改、私有 UI 执行或业务写操作。
