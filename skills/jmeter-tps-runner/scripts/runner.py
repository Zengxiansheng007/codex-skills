"""Fixed entry: python -B -m scripts.runner ... from the skill folder."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from .jmx import inspect_jmx
from .controller import run
from .summary import render
from .host import acknowledge
from .storage import dump


def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('prepare');p.add_argument('--source',required=True)
    p=sub.add_parser('run');p.add_argument('--config',required=True)
    p=sub.add_parser('questions');p.add_argument('--output',required=True)
    p=sub.add_parser('ack-question');p.add_argument('--output',required=True);p.add_argument('--id',required=True);p.add_argument('--receipt',required=True);p.add_argument('--response')
    p=sub.add_parser('render');p.add_argument('--summary',required=True);p.add_argument('--destination',required=True)
    args=parser.parse_args()
    if args.action=='prepare':
        plan=inspect_jmx(args.source)
        print(dump({'source':str(plan.path),'source_sha256':plan.source_hash,'requests':[asdict(e) for e in plan.requests],'groups':[asdict(e) for e in plan.groups]}))
    elif args.action=='run':
        result=run(json.loads(Path(args.config).read_text(encoding='utf-8-sig')))
        print(dump({'status':result['status'],'output':str(Path(args.config).resolve())}))
    elif args.action=='questions':
        print(dump([json.loads(p.read_text(encoding='utf-8')) for p in sorted((Path(args.output)/'questions').glob('*.json'))]))
    elif args.action=='ack-question':
        print(dump(acknowledge(args.output,args.id,args.receipt,args.response)))
    else:
        render(json.loads(Path(args.summary).read_text(encoding='utf-8-sig')),args.destination)


if __name__=='__main__':main()
