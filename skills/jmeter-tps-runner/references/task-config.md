# 每任务配置

配置必须由当前任务的确认生成，不携带默认业务文件或地址。示例中的占位符不是授权目标。

```json
{
  "task_id": "user-confirmed-task-id",
  "source": "<explicit JMX path>",
  "source_sha256": "<prepare result>",
  "jmeter": "<existing jmeter.bat path>",
  "output": "<new task output directory>",
  "minimum": 50,
  "maximum": 500,
  "presets": [50, 100, 200, 500],
  "error_percent": "0.5",
  "p90_ms": 2500,
  "decline_ratio": "0.03",
  "targets": [{"id": "<structural identity>", "prerequisites": [], "confirmed_issue_ids": []}],
  "confirmed": true,
  "authorization_note": "<current user confirmation evidence>"
}
```

minimum/maximum和所有档位为10的正整数倍；首档就是起点，最多4个严格递增粗测档，必须全在确认范围内。预算固定每HTTP最多6轮（粗测与细测合计）。错误率这里填百分数0.5，而内部比较使用比例0.005。每任务都需确认，不静默复用旧阈值。

prerequisites必须是用户确认的结构身份集合；空数组明确表示无前置。confirmed_issue_ids为此次预检产生、已由用户处理的确认类问题ID，不能用来放行unsupported项。确认后源文件变化必须重新预检确认。

输出：`<HTTP名称--稳定身份后缀>/<并发>/report/run-NNN/index.html`和`result/result<并发>-run-NNN.jtl`；每轮另存固定副本、日志和round.json。稳定后缀避免同名及Windows字符替换冲突，原HTTP名字不改。顶层task.json、events.jsonl、snapshot.json、questions、summary.json/md提供审计与汇总。
