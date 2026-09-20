from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest
from scripts.controller import run, validate_config
from scripts.jmx import inspect_jmx, prop, literal
from scripts.process import Execution
from scripts.host import acknowledge
from tests.test_jmx import fixture
from tests.test_report import make_report


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);source=self.root/'source.jmx';source.write_text(fixture(),encoding='utf-8')
        plan=inspect_jmx(source);self.ids=[e.identity for e in plan.requests]
        self.config={'task_id':'synthetic','source':str(source),'source_sha256':plan.source_hash,
                     'jmeter':'fake','output':str(self.root/'output'),'minimum':50,'maximum':500,
                     'presets':[50,100,200,500],'error_percent':'.5','p90_ms':2500,'decline_ratio':'.03',
                     'confirmed':True,'authorization_note':'synthetic test only',
                     'targets':[{'id':i,'prerequisites':[],'confirmed_issue_ids':[]} for i in self.ids]}
        self.calls=[]

    def fake(self, executable, paths, on_started):
        plan=inspect_jmx(paths['plan'])
        enabled=[e.name for e in plan.requests if e.enabled]
        concurrency=literal(prop(plan.nodes[plan.groups[0].identity],'ThreadGroup.num_threads'))
        self.calls.append((enabled,concurrency))
        on_started({'pid':123,'argv':['synthetic'],'started_at':'synthetic-start'})
        label=enabled[-1]
        make_report(paths['report'],label=label,tps=concurrency,count=200)
        Path(paths['jtl']).write_text('label,success\n'+''.join(label+',true\n' for _ in range(200)),encoding='utf-8')
        return Execution(True,0,123,'synthetic-start','synthetic-end',None,('synthetic',))

    def execute(self, executor=None):return run(self.config,executor or self.fake,lambda _: '5.6.3')

    def test_six_rounds_serial_three_targets(self):
        result=self.execute()
        self.assertEqual([len(t['rounds']) for t in result['targets']],[6,6,6])
        self.assertEqual([c for _,c in self.calls[:6]],[50,100,200,500,350,420])
        self.assertEqual([e for e,_ in self.calls],[['A']]*6+[['B']]*6+[['C']]*6)
        self.assertEqual(result['status'],'completed')
        self.assertFalse((self.root/'output/execution.lock').exists())
        summary=(self.root/'output/summary.md').read_text(encoding='utf-8')
        self.assertEqual(summary.count('★最终合格峰值'),3)
        self.assertIn('"9/20/26, 8:00 PM"',summary)
        self.assertEqual(inspect_jmx(self.config['source']).source_hash,self.config['source_sha256'])

    def test_quality_first_ends_and_continues(self):
        def fake(executable,paths,started):
            result=self.fake(executable,paths,started)
            if self.calls[-1][0]==['A']:make_report(paths['report'],label='A',error_pct=1,errors=2,count=200)
            return result
        result=self.execute(fake)
        self.assertEqual([len(t['rounds']) for t in result['targets']],[1,6,6])
        self.assertIsNone(result['targets'][0]['peaks']['qualified_round'])
        question=self.root/'output/questions/target-1-quality.json'
        self.assertEqual(json.loads(question.read_text(encoding='utf-8'))['status'],'queued')
        acknowledge(self.root/'output','target-1-quality','synthetic-host-receipt')
        self.assertEqual(json.loads(question.read_text(encoding='utf-8'))['status'],'submitted-to-host')

    def test_prerequisite_switch(self):
        self.config['targets']=self.config['targets'][:2]
        self.config['targets'][1]['prerequisites']=[self.ids[0]]
        self.execute()
        self.assertEqual([e for e,_ in self.calls],[['A']]*6+[['A','B']]*6)

    def test_report_failure_counted_and_no_retry(self):
        def fake(executable,paths,started):
            result=self.fake(executable,paths,started)
            return Execution(True,1,123,'start','end',None,('synthetic',)) if len(self.calls)==1 else result
        result=self.execute(fake)
        self.assertEqual(len(result['targets'][0]['rounds']),1)
        self.assertEqual(result['status'],'completed-with-technical-issues')
        self.assertEqual(len(self.calls),13)

    def test_unknown_inflight_keeps_lock_no_replay(self):
        def fake(executable,paths,started):
            started({'pid':456,'started_at':'synthetic'})
            raise RuntimeError('unknown child state')
        with self.assertRaises(RuntimeError):self.execute(fake)
        self.assertTrue((self.root/'output/execution.lock').exists())
        with self.assertRaises(FileExistsError):self.execute()
        self.assertEqual(self.calls,[])

    def test_not_confirmed_no_execution(self):
        self.config['confirmed']=False
        with self.assertRaises(ValueError):self.execute()
        self.assertFalse((self.root/'output').exists())

    def test_source_changed_no_execution(self):
        self.config['source_sha256']='wrong'
        with self.assertRaises(ValueError):self.execute()
        self.assertEqual(self.calls,[])

    def test_readable_report_mismatch_keeps_scoring(self):
        self.config['targets']=self.config['targets'][:1]
        def fake(executable,paths,started):
            result=self.fake(executable,paths,started)
            Path(paths['jtl']).write_text('label,success\nA,false\n',encoding='utf-8')
            return result
        result=self.execute(fake)
        self.assertEqual(len(result['targets'][0]['rounds']),6)
        self.assertEqual(result['targets'][0]['peaks']['qualified_round'],4)

    def test_decline_midpoint_state(self):
        self.config['targets']=self.config['targets'][:1]
        def fake(executable,paths,started):
            result=self.fake(executable,paths,started)
            make_report(paths['report'],label='A',tps={50:800,100:1000,200:970,70:1100,150:900,60:1150}[self.calls[-1][1]],count=200)
            return result
        self.execute(fake)
        self.assertEqual([c for _,c in self.calls],[50,100,200,70,150,60])


if __name__=='__main__':unittest.main()
