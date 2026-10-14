import tempfile
import unittest
from pathlib import Path
from xml.sax.saxutils import escape
from scripts.jmx import JmxError, inspect_jmx, parse_bytes, prepare_copy, verify_copy
from scripts.preflight import preflight


def fixture(concurrency_tag='intProp', concurrency='1', extra='', before=''):
    def sampler(name):
        return f'<HTTPSamplerProxy testname="{name}" enabled="true"><stringProp name="HTTPSampler.domain">example.invalid</stringProp><stringProp name="HTTPSampler.path">/{name}</stringProp></HTTPSamplerProxy><hashTree/>'
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!--document comment--><?test before?>
<jmeterTestPlan><hashTree><TestPlan testname="计划" enabled="true"/><hashTree>
<ThreadGroup testname="组" enabled="true"><{concurrency_tag} name="ThreadGroup.num_threads">{escape(concurrency)}</{concurrency_tag}><boolProp name="ThreadGroup.scheduler">true</boolProp><longProp name="ThreadGroup.duration">120</longProp><stringProp name="ThreadGroup.ramp_time">5</stringProp></ThreadGroup><hashTree>
<!--inside--><?test inside?>{before}{sampler('A')}{sampler('B')}{sampler('C')}{extra}
</hashTree></hashTree></hashTree></jmeterTestPlan><?test after?>'''


class JmxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root/'输入.jmx'
        self.dest = self.root/'运行 副本.jmx'
        self.load(fixture())

    def load(self, text):
        self.source.write_text(text, encoding='utf-8')
        self.original = self.source.read_bytes()
        self.plan = inspect_jmx(self.source)
        self.a, self.b, self.c = [e.identity for e in self.plan.requests]

    def prepare(self, target=None, prerequisites=(), **kwargs):
        return prepare_copy(self.source, self.dest, target or self.a, prerequisites, 50, **kwargs)

    def report(self, target=None, prerequisites=(), **kwargs):
        return preflight(self.plan, target or self.a, prerequisites, self.dest, **kwargs)

    def mutate(self, old, new):
        candidate = self.dest.read_text(encoding='utf-8').replace(old, new)
        self.assertNotEqual(candidate, self.dest.read_text(encoding='utf-8'))
        with self.assertRaises(JmxError):
            verify_copy(self.plan, parse_bytes(candidate.encode(), self.dest), self.a, (), 50)

    def test_literal_types_and_duration(self):
        for tag in ['intProp','stringProp']:
            with self.subTest(tag=tag):
                self.load(fixture(tag))
                self.assertEqual(self.report()['current_concurrency'],1)
                self.assertEqual(self.report()['configured_duration_seconds'],120)

    def test_disabled_scheduler_does_not_invent_duration(self):
        self.load(fixture().replace('name="ThreadGroup.scheduler">true','name="ThreadGroup.scheduler">false'))
        report=self.report()
        self.assertFalse(report['ready'])
        self.assertIsNone(report['configured_duration_seconds'])
        self.assertEqual(report['duration_field_seconds'],120)
        self.assertIn('scheduler-disabled',str(report['blocking_issues']))

    def test_source_and_enabled_map(self):
        result=self.prepare()
        self.assertEqual(result['enabled_map'],{self.a:True,self.b:False,self.c:False})
        self.assertEqual(self.source.read_bytes(),self.original)
        self.assertIn('<longProp name="ThreadGroup.duration">120</longProp>',self.dest.read_text(encoding='utf-8'))

    def test_switch_without_prerequisite(self):
        self.prepare()
        result=prepare_copy(self.source,self.root/'b.jmx',self.b,(),100)
        self.assertEqual(result['enabled_map'],{self.a:False,self.b:True,self.c:False})

    def test_switch_with_prerequisite(self):
        result=self.prepare(self.b,(self.a,))
        self.assertEqual(result['enabled_map'],{self.a:True,self.b:True,self.c:False})

    def test_invalid_prerequisite(self):
        for prerequisites in [('unknown',),(self.c,),(self.a,self.a),(self.b,)]:
            with self.subTest(prerequisites=prerequisites),self.assertRaises(JmxError):
                self.prepare(self.b,prerequisites)
        self.assertFalse(self.dest.exists())

    def test_overwrite_and_source_alias(self):
        self.dest.write_bytes(b'keep')
        with self.assertRaises(JmxError):self.prepare()
        with self.assertRaises(JmxError):prepare_copy(self.source,self.source,self.a,(),50)
        self.assertEqual(self.dest.read_bytes(),b'keep')
        self.assertEqual(self.source.read_bytes(),self.original)

    def test_confirmation_hash(self):
        with self.assertRaises(JmxError):self.prepare(expected_source_hash='wrong')

    def test_comments_and_pi(self):
        self.prepare()
        text=self.dest.read_text(encoding='utf-8')
        for token in ['<!--document comment-->','<!--inside-->','<?test before?>','<?test inside?>','<?test after?>']:
            self.assertIn(token,text)
        self.mutate('<!--inside-->','<!--modified-->')
        self.mutate('<?test after?>','<?test changed?>')

    def test_whitelist_mutations(self):
        self.prepare()
        for old,new in [('example.invalid','other.invalid'),('>120<','>121<'),('>5<','>6<'),
                        ('ThreadGroup testname="组" enabled="true"','ThreadGroup testname="组" enabled="false"'),
                        ('<intProp name="ThreadGroup.num_threads">50</intProp>','<stringProp name="ThreadGroup.num_threads">50</stringProp>'),
                        ('testname="C"','testname="D"')]:
            with self.subTest(old=old):self.mutate(old,new)

    def test_extra_and_missing_enabled(self):
        self.prepare()
        self.mutate('testname="A" enabled="true"','testname="A" enabled="false"')
        self.mutate('testname="B" enabled="false"','testname="B" enabled="true"')

    def test_bad_concurrency(self):
        for value in [0,55,-10,True,50.0]:
            with self.subTest(value=value),self.assertRaises(JmxError):
                prepare_copy(self.source,self.dest,self.a,(),value)

    def test_expression_and_invalid_literal(self):
        for value in ['${threads}','0','-1','1.0']:
            with self.subTest(value=value):
                self.load(fixture(concurrency=value))
                self.assertFalse(self.report()['ready'])
                with self.assertRaises(JmxError):self.prepare()

    def test_disabled_ancestor(self):
        self.load(fixture().replace('ThreadGroup testname="组" enabled="true"','ThreadGroup testname="组" enabled="false"'))
        self.assertIn('disabled-ancestor',str(self.report()['blocking_issues']))
        with self.assertRaises(JmxError):self.prepare()

    def test_unknown_active_node(self):
        self.load(fixture(extra='<UnqualifiedSampler enabled="true"/><hashTree/>'))
        self.assertIn('unsupported-node',str(self.report()['blocking_issues']))

    def test_inactive_unknown_preserved(self):
        self.load(fixture(extra='<UnqualifiedSampler enabled="false"/><hashTree/>'))
        self.assertTrue(self.report()['ready'])
        self.prepare()
        self.assertIn('UnqualifiedSampler',self.dest.read_text(encoding='utf-8'))

    def test_same_name_distinct_identity(self):
        self.load(fixture().replace('testname="B"','testname="A"'))
        self.assertNotEqual(self.a,self.b)
        self.assertTrue(self.report()['ready'])
        self.assertIn('duplicate-label',str(self.report(self.b,(self.a,))['blocking_issues']))

    def test_variable_requires_confirmation(self):
        self.load(fixture().replace('/A','/${value}'))
        report=self.report()
        self.assertFalse(report['ready'])
        ids=[x['id'] for x in report['blocking_issues']]
        self.assertTrue(self.report(confirmed_issue_ids=ids)['ready'])
        self.prepare(confirmed_issue_ids=ids)

    def test_stale_confirmation_rejected(self):
        with self.assertRaises(JmxError):self.report(confirmed_issue_ids=['fake'])

    def test_csv_relocation(self):
        (self.root/'data.csv').write_text('x\n1',encoding='utf-8')
        self.load(fixture(before='<CSVDataSet enabled="true"><stringProp name="filename">data.csv</stringProp></CSVDataSet><hashTree/>'))
        self.assertTrue(self.report()['ready'])
        report=preflight(self.plan,self.a,(),self.root/'elsewhere'/'copy.jmx')
        self.assertIn('relative-file-layout',str(report['blocking_issues']))

    def test_missing_csv(self):
        self.load(fixture(before='<CSVDataSet><stringProp name="filename">missing.csv</stringProp></CSVDataSet><hashTree/>'))
        self.assertIn('missing-file',str(self.report()['blocking_issues']))

    def test_dtd_both_encodings(self):
        xml='<!DOCTYPE jmeterTestPlan [<!ENTITY x "value">]><jmeterTestPlan/>'
        for encoding in ['utf-8','utf-16']:
            with self.subTest(encoding=encoding),self.assertRaises(JmxError):
                parse_bytes(xml.encode(encoding),self.source)

    def test_invalid_structure(self):
        with self.assertRaises(JmxError):parse_bytes(b'<jmeterTestPlan><hashTree><TestPlan/></hashTree></jmeterTestPlan>',self.source)

    def test_dynamic_label_is_not_confirmable(self):
        self.load(fixture().replace('testname="A"','testname="${label}"'))
        report=self.report()
        self.assertTrue(any(i['id'].startswith('ambiguous-label') and i['kind']=='unsupported' for i in report['blocking_issues']))

    def test_assertion_change_rejected(self):
        self.load(fixture(extra='<ResponseAssertion enabled="true"><stringProp name="Assertion.test_field">response_code</stringProp></ResponseAssertion><hashTree/>'))
        self.prepare()
        self.mutate('response_code','response_data')

    def test_request_order_rejected(self):
        from scripts.jmx import elements
        self.prepare()
        candidate=inspect_jmx(self.dest)
        node=candidate.nodes[self.b]
        tree=node.parentNode
        subtree=elements(tree)[elements(tree).index(node)+1]
        tree.removeChild(node)
        tree.removeChild(subtree)
        tree.insertBefore(node,candidate.nodes[self.a])
        tree.insertBefore(subtree,candidate.nodes[self.a])
        reparsed=parse_bytes(candidate.document.toxml(encoding='utf-8'),self.dest)
        with self.assertRaises(JmxError):verify_copy(self.plan,reparsed,self.a,(),50)

    def test_controller_change_rejected(self):
        marker='<!--inside-->'
        text=fixture().replace(marker,'<GenericController testname="container" enabled="true"/><hashTree>'+marker)
        text=text.replace('</hashTree></hashTree></hashTree></jmeterTestPlan>', '</hashTree></hashTree></hashTree></hashTree></jmeterTestPlan>')
        self.load(text)
        self.prepare()
        self.mutate('testname="container" enabled="true"','testname="container" enabled="false"')

    def test_cross_group_prerequisite(self):
        text=fixture()
        start=text.index('<ThreadGroup')
        end=text.index('</hashTree></hashTree></hashTree></jmeterTestPlan>')+len('</hashTree>')
        text=text[:end]+text[start:end].replace('testname="组"','testname="组2"')+text[end:]
        self.source.write_text(text,encoding='utf-8')
        plan=inspect_jmx(self.source)
        ids=[e.identity for e in plan.requests]
        with self.assertRaises(JmxError):preflight(plan,ids[4],(ids[0],),self.dest)

    def test_class_mismatch(self):
        self.load(fixture().replace('<HTTPSamplerProxy','<HTTPSamplerProxy testclass="JSR223Sampler"'))
        self.assertIn('class-mismatch',str(self.report()['blocking_issues']))

    def test_concurrency_comment_retained_and_verified(self):
        self.load(fixture().replace('>1</intProp>','>1<!--retain--></intProp>'))
        self.prepare()
        self.assertIn('<!--retain-->',self.dest.read_text(encoding='utf-8'))
        self.mutate('<!--retain-->','<!--changed-->')


if __name__=='__main__':unittest.main()
