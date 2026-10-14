"""WorkBuddy boundary: fixed launch, conservative status, durable real-user receipts."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4

# Works from any cwd using the absolute script path; no installed dependencies.
ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ''):
    sys.path.insert(0, str(ROOT))
from scripts.package_integrity import verify_package, digest, reject_link
from scripts.storage import write_new, atomic_json, dump
from scripts.controller import validate_config, task_spec
from scripts.jmx import inspect_jmx
from scripts.preflight import preflight
from scripts.host import acknowledge as core_acknowledge
from scripts.report import read_report
from scripts.contracts import Phase
from scripts.summary import peaks


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def inside(root, path):
    """Evidence must resolve inside the exact run, without linked components."""
    root = Path(root).resolve()
    raw = Path(path).absolute()
    if raw != root and root not in raw.parents:
        raise ValueError('Evidence path outside task')
    for part in [raw, *raw.parents]:
        if part.exists() or part.is_symlink():
            reject_link(part)
        if part == root:
            break
    resolved = raw.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError('Evidence path escapes task')
    return resolved


def task_root(path):
    raw = Path(path).absolute()
    reject_link(raw)
    root = raw.resolve()
    if not root.is_dir():
        raise ValueError('Task directory missing')
    return root


def load_confirmed(config_path):
    path = Path(config_path).resolve()
    config = read(path)
    validate_config(config)
    if not isinstance(config['authorization_note'], str) or not config['authorization_note'].strip():
        raise ValueError('Current user confirmation evidence required')
    for key in ('source', 'jmeter', 'output'):
        value = Path(config[key]).expanduser()
        config[key] = str((value if value.is_absolute() else path.parent/value).resolve())
    output = Path(config['output'])
    if output == ROOT or ROOT in output.parents:
        raise ValueError('Output must be outside the skill directory')
    if output.exists():
        raise FileExistsError('Existing output cannot be replayed')
    original = inspect_jmx(config['source'])
    if original.source_hash != config['source_sha256']:
        raise ValueError('Input changed since confirmation')
    if not Path(config['jmeter']).is_file():
        raise FileNotFoundError('Confirmed JMeter executable missing')
    for target in config['targets']:
        result = preflight(original, target['id'], target['prerequisites'],
                           output/'copy-preview.jmx', target['confirmed_issue_ids'])
        if not result['ready']:
            raise ValueError('Preflight unresolved for ' + target['id'])
    return config


def supervise(config_path):
    """Foreground supervisor, intended to be owned by the host background task.

    No detach, recovery, timeout retry, live PID killing, or shell interpolation.
    """
    integrity = verify_package()
    config = load_confirmed(config_path)
    root = Path(config['output'])
    root.mkdir(parents=True, exist_ok=False)  # durable exclusive launch reservation
    host = root/'host'
    host.mkdir()
    runtime = host/'runtime'
    runtime.mkdir()
    snapshot = host/'confirmed-config.json'
    write_new(snapshot, config)
    argv = [sys.executable, '-B', '-S', '-P', '-m', 'scripts.runner', 'run', '--config', str(snapshot)]
    run_id = str(uuid4())
    identity = {'run_id': run_id, 'supervisor_pid': os.getpid(),
                'config_sha256': digest(snapshot), 'manifest_sha256': integrity['manifest_sha256'],
                'created_at': now(), 'argv': argv, 'cwd': str(runtime), 'state': 'launch-intent',
                'pid_is_not_liveness_proof': True}
    write_new(host/'launch.json', identity)
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
    child = None
    try:
        with (host/'controller-console.txt').open('xb') as console:
            child = subprocess.Popen(argv, cwd=runtime, env=env, stdout=console,
                                     stderr=subprocess.STDOUT, shell=False,
                                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            identity.update(state='spawned', child_pid=child.pid, spawn_observed_at=now())
            atomic_json(host/'launch.json', identity)
            code = child.wait()
        artifacts = {}
        if code == 0:
            for name in ('summary.json','summary.docx','snapshot.json','task.json'):
                path = inside(root, root/name)
                if path.is_file():
                    artifacts[name] = digest(path)
        write_new(host/'exit.json', {'run_id':run_id, 'config_sha256':identity['config_sha256'],
                  'child_pid':child.pid, 'started':True, 'exit_code':code,
                  'observed_at':now(), 'basis':'owned-child.wait', 'artifacts':artifacts})
        return code
    except BaseException as exc:
        # Keep supervising an owned live child if receipt persistence failed.
        # No restart; a killed supervisor may leave no exit evidence at all.
        try:
            write_new(host/'supervisor-failure.json', {'type':type(exc).__name__,
                      'recorded_at':now(), 'child_spawned':child is not None,
                      'automatic_replay':False})
        except OSError:
            pass
        if child is not None and child.returncode is None:
            child.wait()
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        return 1


def bind_task(output, task_id, receipt):
    if not isinstance(task_id, str) or not task_id.strip() or not receipt.strip():
        raise ValueError('Real host task id and receipt required')
    root = task_root(output)
    launch = read(inside(root, root/'host/launch.json'))
    path = inside(root, root/'host/host-task.json')
    value = {'run_id':launch['run_id'], 'task_id':task_id, 'receipt':receipt,
             'recorded_at':now(), 'attested_by_host':True}
    if path.exists():
        old = read(path)
        if all(old.get(k) == value[k] for k in ('run_id', 'task_id', 'receipt')):
            return old
        raise ValueError('Conflicting host task identity')
    write_new(path, value)
    return value


def pending_questions(output):
    root = task_root(output)
    folder = inside(root, root/'questions')
    result = {'pending':[], 'answered_count':0, 'issues':[], 'queue_complete':True}
    if not folder.exists():
        return result
    if not folder.is_dir():
        raise ValueError('Question queue is not a directory')
    for path in sorted(folder.glob('*.json')):
        try:
            item = read(inside(root, path))
            if not isinstance(item, dict) or item.get('id') != path.stem:
                raise ValueError('Question identity mismatch')
            state = item.get('status')
            if state not in ('queued', 'submitted-to-host', 'answered'):
                raise ValueError('Unknown question state')
            if state == 'answered':
                if not isinstance(item.get('user_response'), str) or not item['user_response'].strip():
                    raise ValueError('Answered question lacks response')
                result['answered_count'] += 1
            else:
                result['pending'].append({k:item.get(k) for k in
                    ('id','title','status','queue_continues','simulated')})
        except (OSError, ValueError, TypeError):
            result['issues'].append({'file':path.name, 'state':'unreadable-or-changing'})
            result['queue_complete'] = False
    return result


def acknowledge(output, question_id, receipt, response=None):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}', question_id):
        raise ValueError('Invalid question identity')
    if not isinstance(receipt, str) or not receipt.strip():
        raise ValueError('Real host receipt required')
    if response is not None and (not isinstance(response, str) or not response.strip()):
        raise ValueError('A real nonempty answer is required')
    root = task_root(output)
    host = inside(root, root/'host')
    if not host.is_dir():
        raise ValueError('Host run evidence missing')
    path = inside(root, root/'questions'/(question_id+'.json'))
    lock = inside(root, host/'ack.lock')
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    wrote_intent = committed = False
    try:
        os.write(fd, dump({'pid':os.getpid(), 'at':now(), 'id':question_id}).encode('utf-8'))
        os.fsync(fd)
        item = read(path)
        if item.get('id') != question_id or item.get('status') not in ('queued','submitted-to-host','answered'):
            raise ValueError('Question identity/state mismatch')
        if item['status'] == 'answered':
            if item.get('user_response') == response and item.get('host_receipt') == receipt:
                return item
            raise ValueError('Answered question cannot be overwritten or downgraded')
        if item['status'] == 'submitted-to-host' and response is None:
            if item.get('host_receipt') == receipt:
                return item
            raise ValueError('Submission identity is already recorded')
        journal = inside(root, host/'question-events.jsonl')
        event = {'id':question_id, 'receipt':receipt, 'response':response,
                 'recorded_at':now(), 'displayed_at':None, 'answered_at':None,
                 'attested_by_host':True, 'action':'answer' if response is not None else 'submit'}
        # A durable intent and retained lock make a half-written acknowledgement visible.
        with journal.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({**event,'phase':'intent'},ensure_ascii=False)+'\n')
            stream.flush(); os.fsync(stream.fileno())
        wrote_intent = True
        updated = core_acknowledge(root, question_id, receipt, response)
        with journal.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({**event,'phase':'committed','recorded_at':now()},ensure_ascii=False)+'\n')
            stream.flush(); os.fsync(stream.fileno())
        committed = True
        return updated
    finally:
        os.close(fd)
        if not wrote_intent or committed:
            lock.unlink()


def _verify_result(root, result, config):
    """Re-use official parsing, never re-score from JTL or model interpretations."""
    if result.get('task_id') != config['task_id'] or result.get('source_sha256') != config['source_sha256']:
        raise ValueError('Task/summary identity mismatch')
    thresholds = result.get('thresholds')
    if not isinstance(thresholds, dict) or str(thresholds.get('error_percent')) != str(config.get('error_percent')) \
            or str(thresholds.get('p90_ms')) != str(config.get('p90_ms')):
        raise ValueError('Summary quality threshold mismatch')
    targets = result['targets']
    if [t['id'] for t in targets] != [t['id'] for t in config['targets']]:
        raise ValueError('Summary target list mismatch')
    technical = False
    for target in targets:
        spec = task_spec(config, target['id'])
        rows = target['rounds']
        if not 1 <= len(rows) <= 6:
            raise ValueError('Missing rounds or exceeded budget')
        for number, row in enumerate(rows, 1):
            if row['number'] != number:
                raise ValueError('Round identity mismatch')
            jtl = inside(root, row['paths']['jtl'])
            record = read(inside(root, jtl.with_suffix('.round.json')))
            if record != row:
                raise ValueError('Summary/round record mismatch')
            if row.get('technical_error'):
                technical = True
                if row.get('metrics') is not None:
                    raise ValueError('Conflicting technical round')
                continue
            if row['execution']['exit_code'] != 0 or not jtl.is_file():
                raise ValueError('Missing successful round artifacts')
            report = inside(root, row['paths']['report'])
            for rel in ('statistics.json','index.html','content/js/dashboard.js'):
                inside(root, report/rel)
            metrics = read_report(report, target['label'], result['runtime_version'])
            fresh = json.loads(dump(asdict(metrics)))
            if fresh != row['metrics']:
                raise ValueError('Official report evidence differs from summary')
            obs = json.loads(dump(asdict(metrics.observation(spec, number, Phase(row['phase']), row['concurrency']))))
            if obs != row['observation']:
                raise ValueError('Quality observation differs from confirmed task')
        if peaks(rows) != target['peaks']:
            raise ValueError('Peak projection mismatch')
    expected = 'completed-with-technical-issues' if technical else 'completed'
    if result['status'] != expected:
        raise ValueError('Technical issue status mismatch')
    if not inside(root, root/'summary.docx').is_file():
        raise ValueError('Summary document missing')


def status(output):
    root = task_root(output)
    projection = {'execution':'unknown', 'ready_for_report':False, 'delivery':'not-recorded',
                  'java_process_state':'not-observed-by-this-reader', 'automatic_replay':False,
                  'issues':[], 'summary_path':str(root/'summary.docx')}
    try:
        projection['questions'] = pending_questions(root)
        if inside(root, root/'host/ack.lock').exists():
            projection['issues'].append('Acknowledgement is in progress or uncertain; do not repeat it')
        failure = inside(root, root/'host/supervisor-failure.json')
        if failure.exists():
            projection['issues'].append('Supervisor failure evidence present')
            return projection
        launch = read(inside(root, root/'host/launch.json'))
        exit_path = inside(root, root/'host/exit.json')
        if not exit_path.exists():
            projection['execution'] = 'running-or-unknown'
            return projection
        ended = read(exit_path)
        for key in ('run_id','config_sha256','child_pid'):
            if key not in launch or launch[key] != ended.get(key):
                raise ValueError('Launch/exit evidence identity mismatch')
        if ended.get('basis') != 'owned-child.wait' or ended.get('started') is not True or type(ended.get('exit_code')) is not int:
            raise ValueError('Actual owned-child exit evidence missing')
        if ended['exit_code'] != 0:
            projection['execution'] = 'controller-exited-unsuccessfully'
            projection['exit_code'] = ended['exit_code']
            return projection
        projection['execution'] = 'incomplete'
        artifacts = ended.get('artifacts', {})
        for name in ('summary.json','summary.docx','snapshot.json','task.json'):
            if artifacts.get(name) != digest(inside(root, root/name)):
                raise ValueError('Completion artifact missing or changed: ' + name)
        if inside(root, root/'execution.lock').exists() or inside(root, root/'failure.json').exists():
            raise ValueError('Core lock/failure conflicts with successful completion')
        config_path = inside(root, root/'host/confirmed-config.json')
        if digest(config_path) != launch['config_sha256']:
            raise ValueError('Confirmed configuration drift')
        config = read(config_path)
        validate_config(config)
        if Path(config['output']).resolve() != root or read(inside(root,root/'task.json')) != config:
            raise ValueError('Configuration/task output mismatch')
        snapshot = read(inside(root, root/'snapshot.json'))
        result = read(inside(root, root/'summary.json'))
        if snapshot.get('state') != 'ended' or snapshot.get('status') != result.get('status'):
            raise ValueError('Core terminal snapshot missing or inconsistent')
        _verify_result(root, result, config)
        projection['execution'] = result['status']
        projection['ready_for_report'] = True
        projection['targets'] = [
            {'id':t['id'],'label':t['label'],'duration_seconds':t.get('duration_seconds'),
             'stop_reason':t['stop_reason'],'peaks':t['peaks'],
             'rounds':[{'number':r['number'],'concurrency':r['concurrency'],'phase':r['phase'],
                        'metrics':({k:r['metrics'][k] for k in
                            ('sample_count','error_count','error_percent','tps','p90_ms','start_time','end_time')}
                            if r.get('metrics') else None), 'technical_error':r.get('technical_error'),
                        'report':r['paths']['report']} for r in t['rounds']]}
            for t in result['targets']]
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, ArithmeticError) as exc:
        projection['issues'].append('Evidence unreadable, incomplete or inconsistent: ' + type(exc).__name__)
    return projection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    commands.add_parser('verify')
    p = commands.add_parser('prepare'); p.add_argument('--source', required=True)
    p = commands.add_parser('run'); p.add_argument('--config', required=True)
    for action in ('status','questions'):
        p = commands.add_parser(action); p.add_argument('--output', required=True)
    p = commands.add_parser('acknowledge'); p.add_argument('--output', required=True)
    p.add_argument('--id', required=True); p.add_argument('--receipt', required=True); p.add_argument('--response')
    p = commands.add_parser('bind-task'); p.add_argument('--output', required=True)
    p.add_argument('--task-id', required=True); p.add_argument('--receipt', required=True)
    args = parser.parse_args()
    if args.action == 'run':
        return supervise(args.config)
    verify_package()
    if args.action == 'verify':
        value = verify_package()
    elif args.action == 'prepare':
        plan = inspect_jmx(args.source)
        value = {'source':str(plan.path),'source_sha256':plan.source_hash,
                 'requests':[asdict(e) for e in plan.requests],'groups':[asdict(e) for e in plan.groups]}
    elif args.action == 'status':
        value = status(args.output)
    elif args.action == 'questions':
        value = pending_questions(args.output)
    elif args.action == 'bind-task':
        value = bind_task(args.output, args.task_id, args.receipt)
    else:
        value = acknowledge(args.output, args.id, args.receipt, args.response)
    print(dump(value))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        sys.exit(main())
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(dump({'status':'failed','error':type(exc).__name__,'detail':str(exc),'automatic_replay':False}),file=sys.stderr)
        sys.exit(1)
