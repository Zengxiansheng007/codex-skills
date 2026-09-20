"""Conservative static qualification; issues never imply user confirmation."""
from pathlib import Path
import re
from .jmx import JmxError, elements, literal, prop, selection, value


SAFE = {'TestPlan', 'ThreadGroup', 'GenericController', 'HTTPSamplerProxy',
        'Arguments', 'HeaderManager', 'CookieManager', 'CacheManager', 'AuthManager',
        'ConfigTestElement', 'CSVDataSet', 'ConstantTimer', 'UniformRandomTimer',
        'GaussianRandomTimer', 'ResponseAssertion', 'DurationAssertion', 'SizeAssertion',
        'JSONPathAssertion', 'ResultCollector', 'RegexExtractor', 'JSONPostProcessor',
        'XPathExtractor', 'XPath2Extractor', 'BoundaryExtractor'}
EXTRACTORS = {'RegexExtractor', 'JSONPostProcessor', 'XPathExtractor', 'XPath2Extractor', 'BoundaryExtractor'}


def preflight(plan, target_id, prerequisite_ids, destination, confirmed_issue_ids=()):
    selected = selection(plan, target_id, prerequisite_ids)
    confirmed = set(confirmed_issue_ids)
    destination = Path(destination).resolve()
    issues = []
    def issue(code, identity, detail, kind='unsupported'):
        issues.append({'id':code + ':' + identity, 'kind':kind, 'detail':detail,
                       'confirmed':kind == 'confirmation' and code + ':' + identity in confirmed})
    def active(e):
        chain = [plan.entries[i] for i in e.ancestors] + [e]
        return all((x.identity in selected) if x.tag == 'HTTPSamplerProxy' else x.enabled for x in chain)
    for identity in selected:
        e = plan.entries[identity]
        if any(not plan.entries[a].enabled for a in e.ancestors):
            issue('disabled-ancestor', identity, 'Required HTTP has a disabled ancestor')
        if not e.name or e.name == 'Total' or '${' in e.name:
            issue('ambiguous-label', identity, 'Empty/reserved/dynamic Statistics label')
    labels = [plan.entries[i].name for i in selected]
    if len(labels) != len(set(labels)):
        issue('duplicate-label', target_id, 'Enabled target/prerequisite labels would merge in Statistics')
    group = plan.entries[target_id].group_id
    node = plan.nodes[group]
    threads = prop(node, 'ThreadGroup.num_threads')
    if threads is None or threads.tagName not in ('intProp', 'stringProp') or literal(threads) is None or literal(threads) < 1:
        issue('unsupported-concurrency', group, 'Expected positive literal intProp/stringProp')
    duration_node = prop(node, 'ThreadGroup.duration')
    raw_duration = literal(duration_node)
    scheduler_node = prop(node, 'ThreadGroup.scheduler')
    scheduler_value = value(scheduler_node).strip().lower() if scheduler_node is not None else 'false'
    scheduler = scheduler_value == 'true'
    duration = raw_duration if scheduler else None
    if scheduler_value not in ('true','false'):
        issue('scheduler-unresolved', group, 'Scheduler expression is not statically qualified')
    elif not scheduler:
        issue('scheduler-disabled', group, 'Duration field does not limit this run; review loop/termination settings before confirming', 'confirmation')
    elif duration is None:
        issue('duration-unresolved', group, 'Configured duration is not a literal; no duration invented', 'confirmation')
    for e in plan.entries.values():
        if not active(e):
            continue
        n = plan.nodes[e.identity]
        if n.hasAttribute('testclass') and n.getAttribute('testclass') != e.tag:
            issue('class-mismatch', e.identity, 'Tag/testclass identity mismatch requires qualification')
        if e.tag not in SAFE:
            issue('unsupported-node', e.identity, 'Unqualified active node: ' + e.tag)
        if e.tag in EXTRACTORS:
            issue('possible-prerequisite', e.identity, 'Extractor may provide data required by another request', 'confirmation')
        text = n.toxml()
        if re.search(r'\$\{', text):
            issue('variable-reference', e.identity, 'Variable/function use requires dependency review', 'confirmation')
        for p in n.getElementsByTagName('*'):
            name = p.getAttribute('name').lower()
            # Known file-bearing properties; never rewrite paths or copy dependencies.
            if name not in {'filename', 'filenamepath', 'httpsampler.implementation.filename',
                            'fileserver.base', 'httpsampler.file_name', 'file.path', 'beanShell.filename'.lower()}:
                continue
            filename = value(p).strip()
            if not filename:
                continue
            if '${' in filename:
                issue('dynamic-file', e.identity, 'File reference cannot be resolved statically')
                continue
            path = Path(filename)
            resolved = path if path.is_absolute() else plan.path.parent / path
            if not resolved.is_file():
                issue('missing-file', e.identity, 'Referenced file is unavailable')
            if not path.is_absolute() and destination.parent != plan.path.parent:
                issue('relative-file-layout', e.identity, 'Copy relocation changes relative file context; layout not qualified')
    ids = {i['id'] for i in issues if i['kind'] == 'confirmation'}
    if confirmed - ids:
        raise JmxError('Unknown/stale issue confirmation')
    blocking = [i for i in issues if not i['confirmed']]
    return {'ready':not blocking, 'issues':issues, 'blocking_issues':blocking,
            'target_id':target_id, 'prerequisite_ids':sorted(selected - {target_id}),
            'current_concurrency':literal(threads), 'configured_duration_seconds':duration,
            'duration_field_seconds':raw_duration, 'scheduler_enabled':scheduler,
            'source_hash':plan.source_hash, 'static_dependency_analysis_complete':False}
