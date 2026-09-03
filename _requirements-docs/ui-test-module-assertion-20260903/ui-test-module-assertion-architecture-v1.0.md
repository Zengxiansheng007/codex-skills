# UI-Test 逐模块断言与产品聚合架构 v1.0

状态：`candidate-as-built`

## 权威数据流

```text
Source Case v2 -----------┐
Test Data v2 -------------+--> Compiler v2 --> Case IR / Resolved IR / Manifest
PageModuleRegistry -------+                 --> Human / Midscene / Playwright
Runtime/Credential refs --┘

A/B validated IR + Display Registry
  --> render_product_aggregate_v2
  --> recursive Outline + Markdown + strict aggregate manifest
```

Source Case 只拥有步骤与断言语义；Test Data 只拥有可编辑业务值和生成规则；Runtime、credential、sequence 分别独立。PageModuleRegistry 只声明页面模块、分支适用方式和断言绑定。

## 关键组件

- `compiler_v2.py`：Schema 后继续执行覆盖矩阵和引用解析；一次生成全部投影。
- `product_aggregate.py`：从 Case/Resolved IR 构造递归产品树，不读取 Human Markdown。
- `case_sync.py`：`prepare_sync_plan` 发布 inactive release，`activate_prepared_sync_plan` 进行 CAS 激活。
- 天津适配器：实现页面定位器、读回断言、B sequence 预览及 formal prepare/activate 编排。
- `PreSubmitQualificationResult`：候选 build 的无写验证凭证，不等价于 R2 成功结果。

## 失败封闭

编译缺口使用 `E_P0_MODULE_COVERAGE_MISSING`、`E_STEP_POSTCONDITION_MISSING`、`E_DEFAULT_EXPECTATION_MISSING`、`E_ASSERTION_TARGET_UNREGISTERED`、`E_COMPOSITE_PAGE_OPERATION_FORBIDDEN`；投影/执行偏移使用 `E_PROJECTION_ASSERTION_DRIFT`。任何失败都不得切 active。

## 激活事务

1. 冻结旧 A/B/product active 与目标文件哈希。
2. prepare 只创建不可变 case/product release，并安装 qualification 必需的 runtime adapter。
3. A/B 分别运行到提交前；B 只读 `next_value`。
4. activate 校验两份 qualification 的 case/branch/build 精确集合。
5. 在产品锁内复核三组 CAS，写 working projections，切 A/B active，最后切 product active；异常按备份恢复指针与 working files。

## 公开边界

GitHub 只发布通用 `skills/ui-test` 与脱敏文档；天津定位器、私有路径值、凭据和运行截图不进入公开仓库。
