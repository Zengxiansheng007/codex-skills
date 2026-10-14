"""All actual rounds; Word (docx) summary written with the standard library only.

The summary document is generated as a minimal WordprocessingML package via
`zipfile`, with no third-party dependency. Display-only rounding and 24-hour
time conversion never replace the official metrics retained in summary.json.
"""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import re
import zipfile


# ── 展示格式化（仅展示，不改评分/选点） ──────────────────

_TWELVE_HOUR = re.compile(r'(\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM)', re.IGNORECASE)


def to_24h(value):
    """把 JMeter 面板的 12 小时时间文本（如 "9/21/26, 2:27 PM"）转为 24 小时制 HH:MM。

    无法识别的文本原样保留，不臆造时间。
    """
    text = str(value).strip().strip('"\'')
    match = _TWELVE_HOUR.search(text)
    if not match:
        return text or str(value)
    hour = int(match.group(1))
    minute = match.group(2)
    ampm = match.group(3).upper()
    if ampm == 'PM' and hour != 12:
        hour += 12
    elif ampm == 'AM' and hour == 12:
        hour = 0
    return f'{hour:02d}:{minute}'


def _round(value, places):
    return format(Decimal(str(value)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP), 'f')


def peaks(rounds):
    readable = [r for r in rounds if r.get('metrics')]
    qualified = [r for r in readable if r['observation']['is_qualified']]

    def rank(r):
        return (Decimal(str(r['metrics']['tps'])), -r['concurrency'])

    best = max(qualified, key=rank) if qualified else None
    observed = max(readable, key=rank) if readable else None
    tied = [r['number'] for r in qualified
            if best and Decimal(str(r['metrics']['tps'])) == Decimal(str(best['metrics']['tps']))]
    return {'qualified_round': best['number'] if best else None,
            'observed_round': observed['number'] if observed else None, 'co_peak_rounds': tied}


# ── 最小 WordprocessingML 文档构建 ──────────────────────

_XML_ESCAPES = {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;'}


def _esc(value):
    return ''.join(_XML_ESCAPES.get(c, c) for c in str(value))


def _run(text, bold=False, size=None):
    rpr = '<w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="宋体"/>'
    if bold:
        rpr += '<w:b/>'
    if size:
        rpr += f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
    rpr += '</w:rPr>'
    return f'<w:r>{rpr}<w:t xml:space="preserve">{_esc(text)}</w:t></w:r>'


def _para(text='', bold=False, size=None, align=None):
    ppr = '<w:pPr>'
    if align:
        ppr += f'<w:jc w:val="{align}"/>'
    ppr += '</w:pPr>'
    body = _run(text, bold, size) if text else ''
    return f'<w:p>{ppr}{body}</w:p>'


def _cell(text, header=False):
    shd = '<w:shd w:val="clear" w:color="auto" w:fill="D9E2F3"/>' if header else ''
    runs = _run(text, bold=header)
    return (f'<w:tc><w:tcPr>{shd}<w:tcW w:w="0" w:type="auto"/></w:tcPr>'
            f'<w:p>{runs}</w:p></w:tc>')


def _row(cells, header=False):
    return '<w:tr>' + ''.join(_cell(c, header=header) for c in cells) + '</w:tr>'


def _border():
    return ('<w:tblBorders>'
            '<w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
            '<w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
            '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
            '<w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
            '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
            '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
            '</w:tblBorders>')


def _table(headers, rows):
    cols = '<w:tblGrid>' + ''.join('<w:gridCol w:w="1500"/>' for _ in headers) + '</w:tblGrid>'
    tblpr = '<w:tblPr><w:tblW w:w="0" w:type="auto"/>' + _border() + '</w:tblPr>'
    thead = _row(headers, header=True)
    tbody = ''.join(_row(r) for r in rows)
    return '<w:tbl>' + tblpr + cols + thead + tbody + '</w:tbl>'


def _write_docx(destination, blocks):
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:body>' + ''.join(blocks) +
                '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
                '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
                'w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>'
                '</w:body></w:document>')
    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/word/document.xml" '
                     'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                     '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/>'
            '</Relationships>')
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', content_types)
        archive.writestr('_rels/.rels', rels)
        archive.writestr('word/document.xml', document)
    return destination


# ── 汇总渲染 ────────────────────────────────────────────

HEADERS = ['并发', '样本数', '错误率', 'P90 (ms)', 'TPS', '起止时间']

APPENDIX_HEADERS = ['轮次', '并发', '错误类型', '错误数', '占错误比(%)', '占样本比(%)']


def _appendix_rows(target):
    """Collect the official per-error-type breakdown appended for a target."""
    rows = []
    for r in target['rounds']:
        metrics = r.get('metrics') or {}
        for item in metrics.get('errors') or ():
            rows.append([str(r['number']), str(r.get('concurrency', '')),
                         str(item.get('type', '')),
                         str(item.get('count', '')),
                         str(item.get('pct_in_errors', '')),
                         str(item.get('pct_in_samples', ''))])
    return rows


def _round_cells(round_):
    metrics = round_.get('metrics')
    if not metrics:
        return ['不可读'] * len(HEADERS)
    return [str(round_['concurrency']),
            str(metrics['sample_count']),
            _round(metrics['error_percent'], 2) + '%',
            _round(metrics['p90_ms'], 2),
            _round(metrics['tps'], 2),
            to_24h(metrics['start_time']) + ' ～ ' + to_24h(metrics['end_time'])]


def render(result, destination):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(str(destination))
    blocks = [_para('JMeter 逐请求压测汇总', bold=True, size=32, align='center'),
              _para('峰值指本次已测档位中的最高合格 TPS，不代表区间内全局最优。'),
              _para('时间来自每轮官方 report，已转换为 24 小时制（HH:MM）。')]
    for index, target in enumerate(result['targets'], 1):
        rounds = target['rounds']
        peak = peaks(rounds)
        levels = '、'.join(str(r['concurrency']) for r in rounds) or '未发压'
        duration = target.get('duration_seconds')
        blocks.append(_para(f'{index}．{target["label"]}', bold=True, size=28))
        blocks.append(_para(f'测试并发：{levels}；持续时间：{duration if duration is not None else "不可解析"} 秒/轮。'))
        blocks.append(_table(HEADERS, [_round_cells(r) for r in rounds]))
        blocks.append(_para(f'结束原因：{target["stop_reason"]}。'))
        if peak['qualified_round'] is None:
            blocks.append(_para('本次未找到满足质量门槛的结果。'))
        else:
            peak_round = next(r for r in rounds if r['number'] == peak['qualified_round'])
            co = [r['number'] for r in rounds
                  if r['number'] in peak['co_peak_rounds'] and r['number'] != peak['qualified_round']]
            suffix = f'（并列第 {"、".join(map(str, co))} 轮）' if co else ''
            blocks.append(_para(f'★最终合格峰值：并发 {peak_round["concurrency"]}'
                                f'（第 {peak["qualified_round"]} 轮）{suffix}。'))
        if peak['observed_round'] is not None:
            observed = next(r for r in rounds if r['number'] == peak['observed_round'])
            quality = '合格。' if observed['observation']['is_qualified'] else '不合格。'
            blocks.append(_para(f'观测最高 TPS：{_round(observed["metrics"]["tps"], 2)}，'
                                f'并发 {observed["concurrency"]}，质量{quality}'))
        for r in rounds:
            link = Path(r['paths']['report']) / 'index.html'
            result_file = Path(r['paths']['jtl'])
            blocks.append(_para(f'- 第 {r["number"]} 轮（{r["phase"]}）：report：{link.as_posix()}；'
                                f'result：{result_file.as_posix()}。'))
        blocks.append(_para(''))
    blocks.append(_para(f'任务状态：{result["status"]}。'))
    blocks.append(_para('附录：报错信息记录', bold=True, size=28))
    appendix = []
    for target in result['targets']:
        rows = _appendix_rows(target)
        if rows:
            appendix.append((target['label'], rows))
    if not appendix:
        blocks.append(_para('无报错信息（本轮各目标未提取到官方错误明细）。'))
    else:
        for label, rows in appendix:
            blocks.append(_para(f'· {label}', bold=True))
            blocks.append(_table(APPENDIX_HEADERS, rows))
            blocks.append(_para(''))
    return _write_docx(destination, blocks)