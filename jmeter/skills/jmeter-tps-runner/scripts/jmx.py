"""JMX structural identity and independently verified, non-overwriting copies.

No JMeter execution. Inputs are explicit local paths; XML content is data.
"""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re
from xml.dom import Node, minidom
from xml.parsers import expat


class JmxError(ValueError):
    pass


def elements(node):
    return [n for n in node.childNodes if n.nodeType == Node.ELEMENT_NODE]


def value(node):
    return ''.join(n.data for n in node.childNodes
                   if n.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE))


def prop(node, name):
    found = [n for n in elements(node) if n.getAttribute('name') == name]
    if len(found) > 1:
        raise JmxError('Duplicate property: ' + name)
    return found[0] if found else None


def literal(node):
    if node is None or elements(node) or not re.fullmatch(r'[0-9]+', value(node).strip()):
        return None
    return int(value(node).strip())


@dataclass(frozen=True)
class Entry:
    identity: str
    tag: str
    name: str
    enabled: bool
    ancestors: tuple[str, ...]
    group_id: str | None
    order: int


@dataclass
class Plan:
    path: Path
    source_hash: str
    document: object
    entries: dict[str, Entry]
    nodes: dict[str, object]

    @property
    def requests(self):
        return tuple(e for e in self.entries.values() if e.tag == 'HTTPSamplerProxy')

    @property
    def groups(self):
        return tuple(e for e in self.entries.values() if e.tag == 'ThreadGroup')


def parse_bytes(data, path):
    # Expat recognizes declarations even with UTF-16; do not use a byte regex.
    parser = expat.ParserCreate()
    def reject(*_):
        raise JmxError('DTD and entity declarations are unsupported')
    parser.StartDoctypeDeclHandler = reject
    parser.EntityDeclHandler = reject
    parser.ExternalEntityRefHandler = reject
    try:
        parser.Parse(data, True)
        doc = minidom.parseString(data)
    except (expat.ExpatError, ValueError) as exc:
        raise JmxError(str(exc)) from exc
    root = doc.documentElement
    if root.tagName != 'jmeterTestPlan':
        raise JmxError('Expected jmeterTestPlan')
    top = elements(root)
    if len(top) != 1 or top[0].tagName != 'hashTree':
        raise JmxError('Expected one root hashTree')
    entries, nodes = {}, {}
    def walk(tree, prefix, ancestors, group):
        children = elements(tree)
        if len(children) % 2:
            raise JmxError('Unpaired JMX element/hashTree')
        for i in range(0, len(children), 2):
            node, subtree = children[i:i+2]
            if node.tagName == 'hashTree' or subtree.tagName != 'hashTree':
                raise JmxError('Invalid JMX element/hashTree order')
            identity = prefix + '/' + str(i // 2)
            state = node.getAttribute('enabled') if node.hasAttribute('enabled') else 'true'
            if state not in ('true', 'false'):
                raise JmxError('Invalid enabled value at ' + identity)
            local_group = identity if node.tagName == 'ThreadGroup' else group
            entries[identity] = Entry(identity, node.tagName, node.getAttribute('testname'),
                                      state == 'true', ancestors, local_group, len(entries))
            nodes[identity] = node
            walk(subtree, identity, ancestors + (identity,), local_group)
    walk(top[0], '', (), None)
    return Plan(Path(path).resolve(), sha256(data).hexdigest(), doc, entries, nodes)


def inspect_jmx(path):
    path = Path(path).resolve()
    return parse_bytes(path.read_bytes(), path)


def selection(plan, target_id, prerequisite_ids):
    prerequisites = tuple(prerequisite_ids)
    if len(prerequisites) != len(set(prerequisites)) or target_id in prerequisites:
        raise JmxError('Duplicate/self prerequisite')
    selected = {target_id, *prerequisites}
    if not selected <= {e.identity for e in plan.requests}:
        raise JmxError('Unknown HTTP identity')
    target = plan.entries[target_id]
    if target.group_id is None:
        raise JmxError('Target has no standard ThreadGroup')
    for identity in prerequisites:
        e = plan.entries[identity]
        if e.group_id != target.group_id or e.ancestors != target.ancestors or e.order >= target.order:
            raise JmxError('Prerequisite must precede target in the same execution context')
    return selected


def validate_concurrency(concurrency):
    if type(concurrency) is not int or concurrency <= 0 or concurrency % 10:
        raise JmxError('Concurrency must be a positive multiple of 10')


def signature(node, ignored_attributes=(), masked_text_nodes=()):
    """Whole-document semantic signature, retaining comments, PI and leaf text."""
    if node.nodeType == Node.ELEMENT_NODE:
        attrs = tuple(sorted((k, v) for k, v in node.attributes.items()
                             if (id(node), k) not in ignored_attributes))
        if id(node) in masked_text_nodes:
            children = ('<allowed-concurrency>', tuple(signature(n) for n in node.childNodes
                         if n.nodeType not in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE)))
        else:
            has_elements = bool(elements(node))
            children = tuple(signature(n, ignored_attributes, masked_text_nodes)
                             for n in node.childNodes
                             if not (has_elements and n.nodeType == Node.TEXT_NODE and not n.data.strip()))
        return ('element', node.tagName, attrs, children)
    if node.nodeType == Node.DOCUMENT_NODE:
        return ('document', tuple(signature(n, ignored_attributes, masked_text_nodes)
                                  for n in node.childNodes
                                  if not (n.nodeType == Node.TEXT_NODE and not n.data.strip())))
    if node.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE):
        return ('text', node.data)
    return (node.nodeType, node.nodeName, node.nodeValue)


def verify_copy(original, candidate, target_id, prerequisite_ids, concurrency):
    """Compare two independently parsed plans, never a generator change list."""
    validate_concurrency(concurrency)
    selected = selection(original, target_id, prerequisite_ids)
    if original.entries.keys() != candidate.entries.keys():
        raise JmxError('Structure changed')
    group = original.entries[target_id].group_id
    p_old = prop(original.nodes[group], 'ThreadGroup.num_threads')
    p_new = prop(candidate.nodes[group], 'ThreadGroup.num_threads')
    if (p_old is None or p_new is None or p_old.tagName not in ('intProp', 'stringProp')
            or literal(p_old) is None or literal(p_old) < 1 or literal(p_new) != concurrency):
        raise JmxError('Invalid concurrency property')
    old_masks, new_masks, mapping, differences = [], [], {}, []
    for e in original.requests:
        new = candidate.entries[e.identity]
        if new.tag != e.tag or new.enabled != (e.identity in selected):
            raise JmxError('HTTP enabled set mismatch')
        # The candidate must carry an explicit boolean for every HTTP sampler.
        if candidate.nodes[e.identity].getAttribute('enabled') not in ('true', 'false'):
            raise JmxError('Missing explicit HTTP enabled')
        old_masks.append((id(original.nodes[e.identity]), 'enabled'))
        new_masks.append((id(candidate.nodes[e.identity]), 'enabled'))
        mapping[e.identity] = new.enabled
        if e.enabled != new.enabled:
            differences.append({'identity':e.identity, 'field':'enabled', 'before':e.enabled, 'after':new.enabled})
    if signature(original.document, old_masks, (id(p_old),)) != signature(candidate.document, new_masks, (id(p_new),)):
        raise JmxError('Change outside concurrency/HTTP enabled whitelist')
    if value(p_old) != value(p_new):
        differences.append({'identity':group, 'field':'ThreadGroup.num_threads',
                            'before':value(p_old), 'after':value(p_new)})
    return {'source_hash':original.source_hash, 'copy_hash':candidate.source_hash,
            'enabled_map':mapping, 'differences':differences}


def prepare_copy(source, destination, target_id, prerequisite_ids, concurrency,
                 confirmed_issue_ids=(), expected_source_hash=None):
    from .preflight import preflight
    validate_concurrency(concurrency)
    original = inspect_jmx(source)
    if expected_source_hash is not None and original.source_hash != expected_source_hash:
        raise JmxError('Source changed since confirmation')
    destination = Path(destination).resolve()
    if destination == original.path or destination.exists():
        raise JmxError('Refusing source alias or existing output')
    prerequisites = tuple(prerequisite_ids)
    report = preflight(original, target_id, prerequisites, destination, confirmed_issue_ids)
    if not report['ready']:
        raise JmxError('Preflight blocked: ' + ', '.join(i['id'] for i in report['blocking_issues']))
    selected = selection(original, target_id, prerequisites)
    # Mutate a separate parse, never the retained source document.
    copy = parse_bytes(original.path.read_bytes(), original.path)
    if copy.source_hash != original.source_hash:
        raise JmxError('Source changed during preparation')
    p = prop(copy.nodes[copy.entries[target_id].group_id], 'ThreadGroup.num_threads')
    for child in list(p.childNodes):
        if child.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE):
            p.removeChild(child)
    p.appendChild(copy.document.createTextNode(str(concurrency)))
    for e in copy.requests:
        copy.nodes[e.identity].setAttribute('enabled', 'true' if e.identity in selected else 'false')
    data = copy.document.toxml(encoding='utf-8')
    verified = verify_copy(original, parse_bytes(data, destination), target_id, prerequisites, concurrency)
    if sha256(original.path.read_bytes()).hexdigest() != original.source_hash:
        raise JmxError('Source changed before writing')
    # Exclusive creation also closes the exists-check/write race.
    with destination.open('xb') as stream:
        stream.write(data)
    verified['copy_path'] = str(destination)
    verified['preflight'] = report
    return verified
