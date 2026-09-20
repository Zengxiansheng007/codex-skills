"""Read JMeter 5.6.3 report artifacts without evaluating JavaScript."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from .contracts import Observation, QualityStatus


class ReportError(ValueError):
    pass


class GeneralInfos(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = self.cell = False
        self.cells, self.rows, self.text = [], [], ''

    def handle_starttag(self, tag, attrs):
        if tag == 'table' and dict(attrs).get('id') == 'generalInfos': self.active = True
        if self.active and tag == 'tr': self.cells = []
        if self.active and tag == 'td': self.cell, self.text = True, ''

    def handle_data(self, text):
        if self.cell: self.text += text

    def handle_endtag(self, tag):
        if self.active and tag == 'td': self.cells.append(self.text.strip()); self.cell = False
        if self.active and tag == 'tr' and len(self.cells) == 2: self.rows.append(self.cells)
        if self.active and tag == 'table': self.active = False


@dataclass(frozen=True)
class ReportMetrics:
    label: str
    sample_count: int
    error_count: int
    error_percent: Decimal
    tps: Decimal
    p90_ms: Decimal
    start_time: str
    end_time: str
    report_path: str
    evidence: dict
    warnings: tuple

    def observation(self, task, number, phase, concurrency):
        quality = (QualityStatus.QUALIFIED if self.error_percent / 100 <= task.error_rate_threshold
                   and self.p90_ms <= task.p90_threshold_ms else QualityStatus.EXCEEDED)
        return Observation(task.target_id, number, phase, concurrency, self.tps,
                           self.p90_ms, self.error_percent / 100, quality)


def numeric(value):
    try:
        if isinstance(value, bool): raise ValueError('Boolean metric')
        result = Decimal(str(value))
        if not result.is_finite() or result < 0: raise ValueError('Nonfinite/negative metric')
        return result
    except (InvalidOperation, ValueError) as exc:
        raise ReportError('Invalid official numeric field') from exc


def read_report(folder, target_label, version='5.6.3'):
    if version != '5.6.3': raise ReportError('Report version not qualified: ' + version)
    if not target_label or target_label == 'Total': raise ReportError('Invalid target Statistics label')
    folder = Path(folder).resolve()
    names = ['statistics.json', 'index.html', 'content/js/dashboard.js']
    try:
        content = {n:(folder/n).read_bytes() for n in names}
        stats = json.loads(content[names[0]], parse_float=Decimal)
        js = content[names[2]].decode('utf-8-sig')
        match = re.search(r'createTable\(\$\("#statisticsTable"\),\s*', js)
        if match is None: raise ReportError('Missing official statistics table metadata')
        table = json.JSONDecoder(parse_float=Decimal).raw_decode(js[match.end():])[0]
        titles = table['titles']
        if titles[0] != 'Label' or titles[11] != 'Transactions/s':
            raise ReportError('Unqualified Statistics column layout')
        positions = [i for i in (8, 9, 10) if titles[i] == '90th pct']
        if len(positions) != 1: raise ReportError('Official report does not identify exactly one P90 column')
        index = positions[0]
        field = f'pct{index-7}ResTime'
        rows = [item for item in table['items'] if item['data'][0] == target_label]
        if len(rows) != 1 or rows[0].get('isController'):
            raise ReportError('Target Statistics row missing, ambiguous or controller')
        row = stats[target_label]
        if row['transaction'] != target_label: raise ReportError('Target identity mismatch')
        count, failures = numeric(row['sampleCount']), numeric(row['errorCount'])
        if count != int(count) or failures != int(failures): raise ReportError('Noninteger sample count')
        error, tps, p90 = numeric(row['errorPct']), numeric(row['throughput']), numeric(row[field])
        parser = GeneralInfos()
        parser.feed(content[names[1]].decode('utf-8-sig'))
        infos = {}
        for key in ('Start Time', 'End Time'):
            found = [v for k,v in parser.rows if k == key]
            if len(found) != 1 or not found[0]: raise ReportError('Missing/ambiguous official ' + key)
            infos[key] = found[0]
        warnings = []
        displayed = rows[0]['data']
        for position, authoritative in [(1,count),(2,failures),(3,error),(index,p90),(11,tps)]:
            # JMeter serializes errorPct through float in statistics.json while
            # the dashboard may retain more digits. Do not flag representation
            # differences below one millionth of a percentage point.
            tolerance = Decimal('0.000001') if position == 3 else Decimal(0)
            if abs(numeric(displayed[position]) - authoritative) > tolerance:
                warnings.append('Official Statistics/dashboard discrepancy at column ' + str(position))
        if failures > count or error > 100 or (count and abs(error - failures*100/count) > Decimal('.01')):
            warnings.append('Official error fields are internally inconsistent; values retained')
        return ReportMetrics(target_label, int(count), int(failures), error, tps, p90,
                             infos['Start Time'], infos['End Time'], str(folder),
                             {'version':version, 'p90_field':field, 'p90_title':titles[index],
                              'display_filter':dict(parser.rows).get('Filter for display','').strip('"'),
                              'hashes':{n:sha256(v).hexdigest() for n,v in content.items()}}, tuple(warnings))
    except (OSError, KeyError, IndexError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReportError('Official report unreadable: ' + type(exc).__name__) from exc
