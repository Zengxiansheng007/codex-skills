from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import workbuddy_bridge as bridge
from scripts.controller import run
from scripts.jmx import inspect_jmx
from scripts.process import Execution
from scripts.storage import atomic_json, write_new
from scripts.host import enqueue
from tests.test_jmx import fixture
from tests.test_report import make_report


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='宿主 space ')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base/'source.jmx'
        self.source.write_text(fixture(),encoding='utf-8')
        plan = inspect_jmx(self.source)
        self.output = self.base/'output'
        self.config = {'task_id':'local-test','source':str(self.source),'source_sha256':plan.source_hash,
            'jmeter':str(self.base/'inert-jmeter.bat'),'output':str(self.output),
            'minimum':50,'maximum':50,'presets':[50],'error_percent':'0.5','p90_ms':2500,
            'decline_ratio':'0.03','confirmed':True,'authorization_note':'offline synthetic only',
            'targets':[{'id':r.identity,'prerequisites':[],'confirmed_issue_ids':[]} for r in plan.requests[:2]]}
        # This file is never executed. All JMeter calls are injected fakes.
        Path(self.config['jmeter']).write_text('INERT TEST FILE',encoding='utf-8')
        self.config_path = self.base/'config.json'
        self.save_config()
        self.calls = 0

    def save_config(self):
        atomic_json(self.config_path,self.config)

    def fake_jmeter(self, executable, paths, on_started):
        self.calls += 1
        plan = inspect_jmx(paths['plan'])
        label = next(e.name for e in plan.requests if e.enabled)
        on_started({'pid':71,'started_at':'synthetic','argv':['never-executed']})
        errors = 200 if self.calls == 1 else 0
        make_report(paths['report'],label=label,count=200,errors=errors,error_pct=100 if errors else 0,p90=80,tps=60)
        Path(paths['jtl']).write_text('label,success\n'+(label+(','+'false' if errors else ',true')+'\n')*200,encoding='utf-8')
        return Execution(True,0,71,'synthetic-start','synthetic-end',None,('never-executed',))

    def completed_run(self, executor=None):
        test = self
        class Child:
            pid = 72
            returncode = None
            def wait(self):
                run(bridge.read(test.output/'host/confirmed-config.json'),executor=executor or test.fake_jmeter,
                    version_probe=lambda _: '5.6.3')
                self.returncode = 0
                return 0
        with patch.object(bridge,'verify_package',return_value={'manifest_sha256':'a'*64}), \
             patch.object(bridge.subprocess,'Popen',return_value=Child()) as spawn:
            code = bridge.supervise(self.config_path)
        self.assertEqual(code,0)
        self.assertEqual(spawn.call_count,1)
        self.assertFalse(spawn.call_args.kwargs['shell'])
        self.assertEqual(Path(spawn.call_args.kwargs['cwd']),self.output/'host/runtime')
        return bridge.read(self.output/'summary.json')

    def test_completed_projection_uses_official_values_and_no_extra_rounds(self):
        result = self.completed_run()
        state = bridge.status(self.output)
        self.assertTrue(state['ready_for_report'],state)
        self.assertEqual(state['execution'],'completed')
        self.assertEqual(self.calls,2)
        self.assertEqual(state['targets'][1]['rounds'][0]['metrics']['p90_ms'],'80')
        self.assertEqual(state['targets'][1]['peaks']['qualified_round'],1)
        self.assertEqual(len(state['questions']['pending']),1)
        self.assertEqual(state['delivery'],'not-recorded')
        self.assertEqual(result['source_sha256'],bridge.digest(self.source))

    def test_unconfirmed_never_creates_output_or_spawns(self):
        self.config['confirmed'] = False; self.save_config()
        with patch.object(bridge,'verify_package'), patch.object(bridge.subprocess,'Popen') as spawn:
            with self.assertRaises(ValueError): bridge.supervise(self.config_path)
        spawn.assert_not_called(); self.assertFalse(self.output.exists())

    def test_source_drift_never_spawns(self):
        self.source.write_text(fixture()+'\n',encoding='utf-8')
        with patch.object(bridge,'verify_package'), patch.object(bridge.subprocess,'Popen') as spawn:
            with self.assertRaises(ValueError): bridge.supervise(self.config_path)
        spawn.assert_not_called(); self.assertFalse(self.output.exists())

    def test_existing_output_refuses_second_launch(self):
        self.completed_run()
        before = (self.output/'host/launch.json').read_bytes()
        with patch.object(bridge,'verify_package'), patch.object(bridge.subprocess,'Popen') as spawn:
            with self.assertRaises(FileExistsError): bridge.supervise(self.config_path)
        spawn.assert_not_called()
        self.assertEqual((self.output/'host/launch.json').read_bytes(),before)

    def test_output_inside_skill_rejected(self):
        self.config['output'] = str(bridge.ROOT/'forbidden-output'); self.save_config()
        with self.assertRaises(ValueError): bridge.load_confirmed(self.config_path)
        self.assertFalse(Path(self.config['output']).exists())

    def test_spawn_failure_preserves_uncertainty(self):
        with patch.object(bridge,'verify_package',return_value={'manifest_sha256':'a'*64}), \
             patch.object(bridge.subprocess,'Popen',side_effect=OSError('fake spawn failure')) as spawn:
            self.assertEqual(bridge.supervise(self.config_path),1)
        self.assertEqual(spawn.call_count,1)
        self.assertTrue((self.output/'host/supervisor-failure.json').exists())
        self.assertFalse(bridge.status(self.output)['ready_for_report'])

    def test_actual_harmless_child_exit_is_waited_and_propagated(self):
        real_popen = subprocess.Popen
        def spawn(argv, **kwargs):
            self.assertEqual(argv[1:6],['-B','-S','-P','-m','scripts.runner'])
            return real_popen([sys.executable,'-B','-c','raise SystemExit(7)'],**kwargs)
        with patch.object(bridge,'verify_package',return_value={'manifest_sha256':'a'*64}), \
             patch.object(bridge.subprocess,'Popen',side_effect=spawn):
            self.assertEqual(bridge.supervise(self.config_path),7)
        evidence = bridge.read(self.output/'host/exit.json')
        self.assertEqual(evidence['exit_code'],7)
        self.assertEqual(evidence['basis'],'owned-child.wait')
        self.assertEqual(bridge.status(self.output)['execution'],'controller-exited-unsuccessfully')

    def test_summary_without_exit_never_means_complete(self):
        self.completed_run(); (self.output/'host/exit.json').unlink()
        state = bridge.status(self.output)
        self.assertFalse(state['ready_for_report'])
        self.assertEqual(state['execution'],'running-or-unknown')

    def test_exit_identity_mismatch_rejected(self):
        self.completed_run()
        p=self.output/'host/exit.json'; data=bridge.read(p); data['child_pid']=999; atomic_json(p,data)
        self.assertFalse(bridge.status(self.output)['ready_for_report'])

    def test_retained_lock_and_running_snapshot_rejected(self):
        self.completed_run(); (self.output/'execution.lock').write_text('unknown',encoding='utf-8')
        self.assertFalse(bridge.status(self.output)['ready_for_report'])
        (self.output/'execution.lock').unlink()
        atomic_json(self.output/'snapshot.json',{'state':'running'})
        self.assertFalse(bridge.status(self.output)['ready_for_report'])

    def test_report_drift_and_missing_report_rejected(self):
        result = self.completed_run()
        p=Path(result['targets'][1]['rounds'][0]['paths']['report'])/'statistics.json'
        content=p.read_text(encoding='utf-8'); p.write_text(content+' ',encoding='utf-8')
        self.assertFalse(bridge.status(self.output)['ready_for_report'])
        p.unlink()
        self.assertFalse(bridge.status(self.output)['ready_for_report'])

    def test_partial_json_not_completed(self):
        self.completed_run(); (self.output/'summary.json').write_text('{',encoding='utf-8')
        self.assertFalse(bridge.status(self.output)['ready_for_report'])

    def test_configuration_drift_not_completed(self):
        self.completed_run()
        p=self.output/'host/confirmed-config.json'; d=bridge.read(p); d['p90_ms']=5000; atomic_json(p,d)
        self.assertFalse(bridge.status(self.output)['ready_for_report'])

    def test_summary_docx_changed_after_exit_is_not_ready_for_delivery(self):
        self.completed_run()
        (self.output/'summary.docx').write_text('P90: forged value',encoding='utf-8')
        self.assertFalse(bridge.status(self.output)['ready_for_report'])

    def test_fixed_module_import_from_separate_cwd_without_site_packages(self):
        self.config['confirmed']=False; self.save_config()
        env=dict(os.environ,PYTHONPATH=str(bridge.ROOT),PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
        command=[sys.executable,'-B','-S','-P','-m','scripts.runner','run','--config',str(self.config_path)]
        result=subprocess.run(command,cwd=self.base,env=env,capture_output=True,timeout=20)
        self.assertNotEqual(result.returncode,0)
        self.assertIn(b'Current task must be explicitly confirmed',result.stderr)
        self.assertFalse(self.output.exists())

    def test_new_absolute_cli_prepare_is_read_only(self):
        command=[sys.executable,'-B',str(bridge.ROOT/'scripts/workbuddy_bridge.py'),'prepare','--source',str(self.source)]
        before=self.source.read_bytes()
        result=subprocess.run(command,cwd=self.base,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(len(json.loads(result.stdout)['requests']),3)
        self.assertEqual(self.source.read_bytes(),before)
        self.assertFalse(self.output.exists())

    def test_technical_completion_is_not_clean_success(self):
        def failed(executable,paths,on_started):
            on_started({'pid':80,'argv':['synthetic'],'started_at':'test'})
            return Execution(True,3,80,'test','test',None,('synthetic',))
        self.completed_run(executor=failed)
        state=bridge.status(self.output)
        self.assertTrue(state['ready_for_report'],state)
        self.assertEqual(state['execution'],'completed-with-technical-issues')
        self.assertIsNone(state['targets'][0]['rounds'][0]['metrics'])

    def test_ack_is_durable_idempotent_and_cannot_downgrade(self):
        self.completed_run()
        q='target-1-quality'
        bridge.acknowledge(self.output,q,'real display receipt')
        self.assertEqual(bridge.pending_questions(self.output)['pending'][0]['status'],'submitted-to-host')
        answer=bridge.acknowledge(self.output,q,'real answer receipt','record only')
        journal=self.output/'host/question-events.jsonl'; before=journal.read_bytes()
        self.assertEqual(bridge.acknowledge(self.output,q,'real answer receipt','record only'),answer)
        self.assertEqual(journal.read_bytes(),before)
        for receipt,response in [('real display receipt',None),('other','record only'),('real answer receipt','rerun')]:
            with self.subTest(response=response),self.assertRaises(ValueError):
                bridge.acknowledge(self.output,q,receipt,response)
        self.assertEqual(bridge.pending_questions(self.output)['answered_count'],1)
        self.assertEqual(self.calls,2)
        for event in [json.loads(x) for x in journal.read_text(encoding='utf-8').splitlines()]:
            self.assertIsNone(event['displayed_at']); self.assertIsNone(event['answered_at'])

    def test_missing_receipt_empty_response_and_path_escape_rejected(self):
        self.completed_run()
        for q,receipt,response in [('target-1-quality','',None),('target-1-quality','receipt',' '),('../target','receipt','answer')]:
            with self.subTest(q=q,receipt=receipt,response=response),self.assertRaises(ValueError):
                bridge.acknowledge(self.output,q,receipt,response)

    def test_second_question_remains_queued_and_answer_does_not_rerun(self):
        self.completed_run(); enqueue(self.output,'target-2-quality','second synthetic question')
        bridge.acknowledge(self.output,'target-1-quality','real receipt','record only')
        q=bridge.pending_questions(self.output)
        self.assertEqual([x['id'] for x in q['pending']],['target-2-quality'])
        self.assertEqual(self.calls,2)

    def test_ack_busy_and_failed_commit_never_replayed(self):
        self.completed_run(); lock=self.output/'host/ack.lock'; lock.write_text('other writer',encoding='utf-8')
        with self.assertRaises(FileExistsError): bridge.acknowledge(self.output,'target-1-quality','receipt','answer')
        lock.unlink()
        with patch.object(bridge,'core_acknowledge',side_effect=OSError('synthetic persistence failure')):
            with self.assertRaises(OSError): bridge.acknowledge(self.output,'target-1-quality','receipt','answer')
        self.assertTrue(lock.exists())
        self.assertTrue(bridge.status(self.output)['issues'])

    def test_partial_question_visible_as_uncertainty(self):
        self.completed_run(); (self.output/'questions/target-2-quality.json').write_text('{',encoding='utf-8')
        self.assertFalse(bridge.pending_questions(self.output)['queue_complete'])

    def test_host_task_binding_is_not_process_exit(self):
        self.completed_run()
        first=bridge.bind_task(self.output,'real-host-task','real-tool-receipt')
        self.assertEqual(bridge.bind_task(self.output,'real-host-task','real-tool-receipt'),first)
        with self.assertRaises(ValueError): bridge.bind_task(self.output,'different-task','real-tool-receipt')
        (self.output/'host/exit.json').unlink()
        self.assertFalse(bridge.status(self.output)['ready_for_report'])

    def test_evidence_path_escape_rejected(self):
        self.completed_run()
        with self.assertRaises(ValueError): bridge.inside(self.output,self.source)


if __name__ == '__main__': unittest.main()
