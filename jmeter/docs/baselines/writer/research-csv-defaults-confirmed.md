> 公开投影：业务规则与原编号保留；“本轮”指源文档编写阶段。源哈希、路径适配与当前发布范围见 jmeter/docs/publication-context.md 及导出清单。

# CSV Data Set Config 默认循环核对

日期：2026-10-13。仅查Apache官方手册和固定rel/v5.6.3源码；未执行JMeter、未读取真实Cookie、未开发。

## 已核事实

JMeter CSV Data Set Config的Recycle on EOF控制文件末尾后重新读取；默认true。Stop thread on EOF默认false，Sharing Mode默认All threads。GUI/BeanInfo定义以及运行类均有对应配置；CSVDataSet在每次主迭代读取并写入线程变量。

- [官方组件手册](https://jmeter.apache.org/usermanual/component_reference.html#CSV_Data_Set_Config)
- [5.6.3 BeanInfo默认值，L83–92](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/components/src/main/java/org/apache/jmeter/config/CSVDataSetBeanInfo.java#L83)
- [5.6.3读取/变量赋值及表头处理，L150–207](https://github.com/apache/jmeter/blob/rel/v5.6.3/src/components/src/main/java/org/apache/jmeter/config/CSVDataSet.java#L150)

因此，用户选择“从第一行继续循环使用”可以直接用原生配置实现，无需写读取/分配算法。生成JMX应显式配置recycle=true，而不是仅凭文件后缀.csv就宣称会循环。既有JMX若已将recycle改为false，其行为按实际配置；不得假称所有CSVDataSet实例必然循环。

如果文件有表头，应从首条数据记录循环，不能把列名cookie当Cookie值。读取策略只复用文件已有内容，不重新登录或延长Cookie有效期；每轮重新生成Cookie仍由已确认的自动认证setUp流程负责。

## 本轮用户选择与设计默认分开

- 用户明确选择末行后循环复用：已确认。
- 默认All threads、Stop thread=false是官方原生默认；writer可显式写入，作为实现默认交付说明，不附加每线程固定账号保证。
- UTF-8、表头、列名/引用的具体输出契约尚需和真实输入一起细化，本研究不替代完整需求确认。

本次是来源核对，不是Cookie读取或CSV导出的实测验收。
