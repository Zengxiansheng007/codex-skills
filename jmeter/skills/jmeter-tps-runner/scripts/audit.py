"""Read-only JTL corroboration. Never change an official Observation."""
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path


def audit_jtl(path, metrics, comparison_profile='unknown'):
    findings = list(metrics.warnings)
    count = errors = 0
    if metrics.evidence.get('display_filter'):
        return {'status':'not-comparable','findings':['Report filter is present; establish a matching JTL scope before interpreting count differences'], 'changes_scoring':False}
    if comparison_profile not in ('unknown','same-label-unfiltered'):
        return {'status':'not-comparable','findings':['Unqualified comparison profile'], 'changes_scoring':False}
    try:
        with Path(path).open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            if not {'label','success'} <= set(reader.fieldnames or []):
                return {'status':'not-comparable','findings':['JTL lacks label/success columns'], 'changes_scoring':False}
            for row in reader:
                if row['label'] != metrics.label: continue
                # Aggregated/distributed sample counts need a separate qualified adapter.
                if row.get('SampleCount', row.get('sampleCount', '1')) not in ('', '1'):
                    return {'status':'not-comparable','findings':['Aggregated JTL rows are not qualified'], 'changes_scoring':False}
                if row['success'].lower() not in ('true','false'): raise ValueError('Invalid success')
                count += 1
                errors += row['success'].lower() == 'false'
        if count != metrics.sample_count: findings.append(f'Target sample count differs: report={metrics.sample_count}, JTL={count}')
        if errors != metrics.error_count: findings.append(f'Target error count differs: report={metrics.error_count}, JTL={errors}')
        if comparison_profile=='unknown' and (count!=metrics.sample_count or errors!=metrics.error_count):
            findings.append('Filtering/aggregation scope is not verified; count differences alone do not prove a report error')
        status=('not-comparable' if comparison_profile=='unknown' and (count!=metrics.sample_count or errors!=metrics.error_count)
                else ('warning' if findings else ('consistent' if comparison_profile=='same-label-unfiltered' else 'counts-match-scope-unverified')))
        return {'status':status, 'findings':findings,
                'jtl_samples':count,'jtl_errors':errors,'changes_scoring':False,
                'limits':'Counts only; no JTL-derived TPS/P90 or timing replaces official report'}
    except (OSError, UnicodeError, csv.Error, ValueError, InvalidOperation):
        return {'status':'not-comparable','findings':['JTL unreadable or unsupported'], 'changes_scoring':False}
