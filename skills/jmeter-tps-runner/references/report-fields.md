# 官方报告字段

已资格验证的版本为 JMeter 5.6.3。读取 `statistics.json` 的目标 HTTP 标签行：sampleCount、errorCount、errorPct（百分数）、throughput（次/秒）。不读取 Total 或前置请求作为目标指标。

P90 先读取官方 `content/js/dashboard.js` 中 statisticsTable 的 titles，第8/9/10列对应 pct1/2/3ResTime；只有实际标题为 `90th pct` 的字段才作为毫秒P90。不执行JavaScript，不假设pct1总是P90。无P90或标签歧义为不可读，不填0或追加复测。

时间直接取 `index.html` 的 generalInfos 中 Start Time/End Time 显示文本，保留原有精度和时区语义。记录各来源SHA256。

JTL只做同标签样本数和错误数核验；缺字段或聚合格式标记不可比。官方各字段相互矛盾或与JTL不一致时提示，仍以官方Statistics参与评分和选点，不改数据、不自动补测。不能凭只读计数核验保证报告完全正确。

错误率两份官方产物在小于等于0.000001个百分点的表示精度差异不作为异常；保留Statistics原值。存在过滤或未验证过滤/聚合口径且计数不同，标为不可比并解释线索，不能声称报告错误。只有已验证的`same-label-unfiltered`口径允许输出同口径计数核验结论；默认是unknown。

格式依据为本项目使用官方 JMeter 5.6.3 从合成CSV实际生成的报告，实测证据保存在项目 report-qualification 目录。真实运行资格单独验证。
