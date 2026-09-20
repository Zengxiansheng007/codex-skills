"""All actual rounds; peaks retain their original official report metrics."""
from decimal import Decimal
from pathlib import Path
from .storage import write_new


def escape(value):
    return str(value).replace('|','\\|').replace('\n',' ').replace('<','&lt;').replace('>','&gt;')


def peaks(rounds):
    readable=[r for r in rounds if r.get('metrics')]
    qualified=[r for r in readable if r['observation']['is_qualified']]
    def rank(r):return (Decimal(str(r['metrics']['tps'])),-r['concurrency'])
    best=max(qualified,key=rank) if qualified else None
    observed=max(readable,key=rank) if readable else None
    tied=[r['number'] for r in qualified if best and Decimal(str(r['metrics']['tps']))==Decimal(str(best['metrics']['tps']))]
    return {'qualified_round':best['number'] if best else None,
            'observed_round':observed['number'] if observed else None,'co_peak_rounds':tied}


def render(result, destination):
    destination=Path(destination)
    lines=['# JMeter 逐请求压测汇总','',
           '峰值指本次已测档位中的最高合格 TPS，不代表区间内全局最优。',
           '时间直接来自每轮官方 report，可能包含前置样本并保留官方显示精度。','']
    for index,target in enumerate(result['targets'],1):
        rounds=target['rounds']; peak=peaks(rounds)
        levels='、'.join(str(r['concurrency']) for r in rounds) or '未发压'
        duration=target.get('duration_seconds')
        lines += [f'**{index}．{escape(target["label"])}**','',
                  f'测试并发：{levels}；持续时间：{duration if duration is not None else "不可解析"} 秒/轮。','',
                  '| 并发数 | 样本数 | 90%响应时间（ms） | TPS（次/秒） | 错误率（%） | 开始时间～结束时间 |',
                  '| --- | --- | --- | --- | --- | --- |']
        for r in rounds:
            m=r.get('metrics')
            mark=' **★最终合格峰值**' if peak['qualified_round']==r['number'] else (' （并列峰值）' if r['number'] in peak['co_peak_rounds'] else '')
            if m:
                lines.append(f'| {r["concurrency"]}{mark} | {m["sample_count"]} | {m["p90_ms"]} | {m["tps"]} | {m["error_percent"]} | {escape(m["start_time"])}～{escape(m["end_time"])} |')
            else:
                lines.append(f'| {r["concurrency"]} | 不可读 | 不可读 | 不可读 | 不可读 | 不可读 |')
        lines += ['',f'结束原因：{escape(target["stop_reason"])}。']
        if peak['qualified_round'] is None:lines.append('本次未找到满足质量门槛的结果。')
        if peak['observed_round'] is not None:
            observed=next(r for r in rounds if r['number']==peak['observed_round'])
            lines.append(f'观测最高 TPS：{observed["metrics"]["tps"]}，并发 {observed["concurrency"]}，质量'+('合格。' if observed['observation']['is_qualified'] else '不合格。'))
        for r in rounds:
            link=Path(r['paths']['report'])/'index.html'
            lines.append(f'- 第 {r["number"]} 轮（{r["phase"]}）：[report](<{link.as_posix()}>)；[result](<{Path(r["paths"]["jtl"]).as_posix()}>)。')
            for warning in r.get('audit',{}).get('findings',[]):lines.append('  核验提示：'+escape(warning))
        lines.append('')
    lines += ['任务状态：'+result['status']+'。','']
    with destination.open('x',encoding='utf-8') as stream:stream.write('\n'.join(lines))
    return destination
