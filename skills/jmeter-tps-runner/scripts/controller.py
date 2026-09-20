"""Single-process deterministic orchestration. No live replay/retry path."""
from dataclasses import asdict
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from .contracts import TaskSpec, Phase
from .search import decide_next
from .jmx import inspect_jmx, prepare_copy, verify_copy
from .preflight import preflight
from .process import run_jmeter, version
from .report import read_report, ReportError
from .audit import audit_jtl
from .storage import Store, write_new, atomic_json
from .host import enqueue
from .summary import render, peaks


def validate_config(config):
    required={'task_id','source','source_sha256','jmeter','output','minimum','maximum','presets',
              'error_percent','p90_ms','targets','confirmed','authorization_note','decline_ratio'}
    missing=required-set(config)
    if missing:raise ValueError('Missing task confirmation fields: '+','.join(sorted(missing)))
    if config['confirmed'] is not True or not config['authorization_note']:
        raise ValueError('Current task must be explicitly confirmed')
    for v in [config['minimum'],config['maximum'],*config['presets']]:
        if type(v) is not int or v<=0 or v%10:raise ValueError('Concurrency must be a positive multiple of 10')
    if len(config['presets'])>4:raise ValueError('At most four coarse presets')
    if Decimal(str(config['decline_ratio'])) != Decimal('.03'):raise ValueError('Approved coarse decline is 3%')
    for key in ['error_percent','p90_ms']:
        if not Decimal(str(config[key])).is_finite():raise ValueError('Nonfinite threshold')
    if not config['targets'] or len({t['id'] for t in config['targets']})!=len(config['targets']):
        raise ValueError('Empty/duplicate target list')
    for target in config['targets']:
        if not {'id','prerequisites','confirmed_issue_ids'} <= set(target):raise ValueError('Explicit prerequisites and issue confirmations required')
        task_spec(config,target['id'])
    return config


def task_spec(config, identity):
    return TaskSpec(config['task_id'],identity,(config['minimum'],config['maximum']),
                    tuple(config['presets']),config['presets'][0],Decimal(str(config['error_percent']))/100,
                    Decimal(str(config['p90_ms'])),Decimal(str(config['decline_ratio'])))


def run(config, executor=run_jmeter, version_probe=version):
    validate_config(config)
    original=inspect_jmx(config['source'])
    if original.source_hash!=config['source_sha256']:raise ValueError('Input changed since confirmation')
    actual_version=version_probe(config['jmeter'])
    if actual_version!='5.6.3':raise ValueError('Unqualified runtime')
    # Qualify every selected target before starting any process.
    qualified={}
    for target in config['targets']:
        preview=Path(config['output'])/'copy-preview.jmx'
        p=preflight(original,target['id'],target['prerequisites'],preview,target['confirmed_issue_ids'])
        if not p['ready']:raise ValueError('Preflight unresolved for '+target['id']+': '+str(p['blocking_issues']))
        qualified[target['id']]=p
    store=Store(config['output'])
    result={'task_id':config['task_id'],'status':'running','targets':[],
            'source_sha256':original.source_hash,'runtime_version':actual_version}
    try:
        write_new(store.root/'task.json',config)
        store.event('task-confirmed',config=config)
        for index,target in enumerate(config['targets'],1):
            identity=target['id'];spec=task_spec(config,identity)
            outcome={'id':identity,'label':original.entries[identity].name,'rounds':[],
                     'duration_seconds':qualified[identity]['configured_duration_seconds'],'stop_reason':'running'}
            result['targets'].append(outcome)
            observations=[];state={};previous_tps=None
            while True:
                decision=decide_next(spec,observations,**state)
                store.event('decision',target_id=identity,decision=decision)
                if decision.action=='end_target':
                    outcome['stop_reason']=decision.reason
                    break
                number=len(observations)+1;concurrency=decision.next_concurrency
                paths=store.paths(outcome['label'],identity,concurrency,number)
                prepared=prepare_copy(config['source'],paths['plan'],identity,target['prerequisites'],concurrency,
                                      target['confirmed_issue_ids'],original.source_hash)
                verified=verify_copy(inspect_jmx(config['source']),inspect_jmx(paths['plan']),identity,target['prerequisites'],concurrency)
                if verified['copy_hash']!=prepared['copy_hash']:raise ValueError('Prepared copy changed')
                store.event('prepared',target_id=identity,number=number,paths=paths,verification=verified)
                # A durable intent must precede spawn; uncertainty is never replayed.
                atomic_json(store.root/'snapshot.json',{'state':'in-flight-unknown','target_id':identity,'number':number,'paths':paths})
                def started(evidence):
                    store.event('started',target_id=identity,number=number,**evidence)
                    atomic_json(store.root/'snapshot.json',{'state':'running','target_id':identity,'number':number,**evidence})
                execution=executor(config['jmeter'],paths,started)
                store.event('process-ended',target_id=identity,number=number,execution=execution)
                if not execution.started:
                    raise RuntimeError('Shared process launch failure; no round counted')
                row={'number':number,'concurrency':concurrency,'phase':decision.next_phase.value,
                     'paths':{k:str(v) for k,v in paths.items()},'execution':asdict(execution),
                     'decision':asdict(decision),'verification':verified,'metrics':None,'observation':None}
                outcome['rounds'].append(row)
                try:
                    if execution.exit_code != 0:raise ReportError('JMeter process exited '+str(execution.exit_code))
                    metrics=read_report(paths['report'],outcome['label'],actual_version)
                    observation=metrics.observation(spec,number,decision.next_phase,concurrency)
                    row['metrics']=asdict(metrics);row['observation']=asdict(observation)
                    row['audit']=audit_jtl(paths['jtl'],metrics)
                    if previous_tps is not None and previous_tps>0 and abs(metrics.tps-previous_tps)/previous_tps>=Decimal('.03'):
                        row['audit']['findings'].append('TPS较相邻轮变化达到3%；这是核验线索，不证明报告错误或系统瓶颈，仍采用report。')
                    previous_tps=metrics.tps
                    observations.append(observation)
                    if number==1 and not observation.is_qualified:
                        enqueue(store.root,f'target-{index}-quality',f'{outcome["label"]} 首轮质量超标，已结束该请求并继续后续请求。是否需要另行处理？')
                    if row['audit']['findings']:store.event('audit-warning',target_id=identity,number=number,audit=row['audit'])
                except ReportError as exc:
                    row['technical_error']=str(exc)
                    outcome['stop_reason']='本目标技术问题：'+str(exc)+'；不自动重发'
                    enqueue(store.root,f'target-{index}-technical',outcome['label']+'：'+outcome['stop_reason']+'。后续请求继续。')
                write_new(Path(paths['jtl']).with_suffix('.round.json'),row)
                atomic_json(store.root/'progress.json',result)
                atomic_json(store.root/'snapshot.json',{'state':'recorded','target_id':identity,'number':number})
                if row['metrics'] is None:break
                state={'current_phase':decision.next_phase,'current_center':decision.center_concurrency,
                       'current_left_endpoint':decision.left_endpoint,'current_right_endpoint':decision.right_endpoint,
                       'current_side':decision.side}
            outcome['peaks']=peaks(outcome['rounds'])
            store.event('target-ended',target_id=identity,stop_reason=outcome['stop_reason'],peaks=outcome['peaks'])
            atomic_json(store.root/'progress.json',result)
        if sha256(Path(config['source']).read_bytes()).hexdigest()!=original.source_hash:raise ValueError('Original input changed during task')
        result['status']='completed-with-technical-issues' if any(any('technical_error' in r for r in t['rounds']) for t in result['targets']) else 'completed'
        write_new(store.root/'summary.json',result)
        render(result,store.root/'summary.md')
        store.event('task-ended',status=result['status'])
        atomic_json(store.root/'snapshot.json',{'state':'ended','status':result['status']})
        store.finish()
        return result
    except BaseException as exc:
        store.abandon()
        # Keep the lock and last durable snapshot. Never infer no load from a crash.
        try:write_new(store.root/'failure.json',{'type':type(exc).__name__,'message':str(exc),'automatic_replay':False})
        except OSError:pass
        raise
