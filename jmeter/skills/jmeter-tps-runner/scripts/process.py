"""Official JMeter invocation and Windows argument boundary; no retries."""
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess


def windows_batch_command(executable, args):
    values=[str(executable),*map(str,args)]
    # cmd expands percent references even inside quotes. Reject such paths;
    # never rename the user's inputs or claim support without a probe.
    if any(any(c in value for c in ('"','%','!','\r','\n','\x00')) for value in values):
        raise ValueError('Unsupported batch argument character: quote, %, ! or control character')
    quoted=' '.join('"'+value+'"' for value in values)
    comspec=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/cmd.exe'
    return f'"{comspec}" /d /v:off /s /c "{quoted}"'


def command(executable, args):
    executable=Path(executable).resolve()
    if not executable.is_file(): raise FileNotFoundError(str(executable))
    if executable.suffix.lower() in ('.bat','.cmd'):
        if os.name!='nt': raise ValueError('Batch files require Windows')
        return windows_batch_command(executable,args)
    return [str(executable),*map(str,args)]


@dataclass(frozen=True)
class Execution:
    started: bool
    exit_code: int | None
    pid: int | None
    started_at: str | None
    ended_at: str | None
    error: str | None
    argv: tuple


def run_jmeter(executable, paths, on_started):
    args=('-n','-t',str(paths['plan']),'-l',str(paths['jtl']),'-e','-o',str(paths['report']),'-j',str(paths['log']))
    argv=(str(Path(executable).resolve()),*args)
    for key in ('jtl','report','log','console'):
        if Path(paths[key]).exists(): raise FileExistsError(str(paths[key]))
    cmd=command(executable,args)
    with Path(paths['console']).open('xb') as log:
        try:
            child=subprocess.Popen(cmd,cwd=Path(paths['plan']).parent,stdout=log,stderr=subprocess.STDOUT,
                                   shell=False,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except OSError as exc:
            return Execution(False,None,None,None,None,type(exc).__name__,argv)
        start=datetime.now(timezone.utc).isoformat()
        try:
            on_started({'pid':child.pid,'started_at':start,'argv':argv})
        except BaseException:
            # Do not leave a live process overlapping a later target, even if
            # persistence failed. Wait for this exact launched child to exit.
            child.wait()
            raise
        exit_code=child.wait()
        return Execution(True,exit_code,child.pid,start,datetime.now(timezone.utc).isoformat(),None,argv)


def version(executable):
    result=subprocess.run(command(executable,('-v',)),capture_output=True,text=True,
                          encoding='utf-8',errors='replace',timeout=60,
                          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode: raise RuntimeError('JMeter version probe failed')
    import re
    found=re.search(r'(?<!\d)(5\.6\.3)(?!\d)',result.stdout+result.stderr)
    if not found: raise ValueError('Only JMeter 5.6.3 is qualified')
    return found.group(1)
