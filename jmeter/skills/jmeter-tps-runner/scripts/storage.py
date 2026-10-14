"""Single-writer local task storage, append-only events, exclusive run paths."""
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json
import os
from pathlib import Path
import re


def encode(value):
    if is_dataclass(value): return asdict(value)
    if isinstance(value, (Decimal, Path)): return str(value)
    if isinstance(value, Enum): return value.value
    raise TypeError(type(value).__name__)


def dump(value):
    return json.dumps(value, ensure_ascii=False, indent=2, default=encode, allow_nan=False)


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        stream.write(dump(value)+'\n'); stream.flush(); os.fsync(stream.fileno())


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    with temporary.open('x', encoding='utf-8') as stream:
        stream.write(dump(value)+'\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)


def folder_name(name, identity):
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip().rstrip('. ')
    if not clean or clean.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:
        clean = 'request-' + clean
    # Stable suffix prevents same-name and sanitized-name collisions.
    return clean[:70] + '--' + sha256(identity.encode()).hexdigest()[:10]


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = self.root/'execution.lock'
        # Never remove an old lock automatically, regardless of PID liveness.
        self.fd = os.open(self.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(self.fd, dump({'pid':os.getpid(),'status':'active-or-unknown'}).encode('utf-8'))
        os.fsync(self.fd)
        self.sequence = 0
        self.previous = None
        if (self.root/'events.jsonl').exists() or (self.root/'task.json').exists():
            os.close(self.fd); self.fd=None
            raise FileExistsError('Existing task cannot be replayed; use render only or a new explicitly authorized task')

    def event(self, kind, **data):
        self.sequence += 1
        record = {'sequence':self.sequence,'at':datetime.now(timezone.utc).isoformat(),
                  'kind':kind,'previous_hash':self.previous,**data}
        payload = dump(record)
        record['hash'] = sha256(payload.encode()).hexdigest()
        with (self.root/'events.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(record,ensure_ascii=False,default=encode)+'\n')
            stream.flush(); os.fsync(stream.fileno())
        self.previous=record['hash']
        return record

    def paths(self, label, identity, concurrency, number):
        target = self.root/folder_name(label,identity)
        base=target/str(concurrency)
        for part in ['report','result','plans']: (base/part).mkdir(parents=True,exist_ok=True)
        report=base/'report'/f'run-{number:03d}'
        jtl=base/'result'/f'result{concurrency}-run-{number:03d}.jtl'
        plan=base/'plans'/f'run-{number:03d}.jmx'
        log=base/'result'/f'jmeter-run-{number:03d}.log'
        console=base/'result'/f'console-run-{number:03d}.txt'
        for p in (report,jtl,plan,log,console):
            if p.exists(): raise FileExistsError(str(p))
        return {'report':report,'jtl':jtl,'plan':plan,'log':log,'console':console}

    def finish(self):
        if self.fd is not None:
            os.close(self.fd); self.fd=None
            self.lock.unlink()

    def abandon(self):
        if self.fd is not None: os.close(self.fd); self.fd=None
        # Retain execution.lock after uncertain termination.
