import sys
from pathlib import Path
sys.path.append(str(next((p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').exists()),Path('/opt/kpi'))/'poc/remote-cuda'))
"""Reuse reviewed child/timeout/CUDA sampling; service owns the one durable ledger."""
import os
from pathlib import Path
import signal
import sys
import time
from staged_child import identity
from common import atomic
from worker import hardware, run_phase


def stop_interrupted(output):
    registry=output/'supervision.json'
    if not registry.exists(): return
    import json
    expected=json.loads(registry.read_text());group=expected['group']
    if not isinstance(group,int) or group<=1 or group==os.getpgrp():
        raise ValueError('invalid saved process group')
    try:
        if identity(group)==expected: os.killpg(group,signal.SIGKILL)
    except ProcessLookupError: pass
    except FileNotFoundError: pass


def execute(package, assets, target_sha, output, deadline, *, cuda=True, command=None):
    # command is a Python-only test seam. Production service cannot select it.
    # All container CLI paths always select the fixed reviewed executable.
    gpu=hardware() if cuda else {'uuid':'SYNTHETIC-CPU-TEST-NOT-GPU'}
    atomic(output/'hardware.json',gpu)
    remaining=deadline-time.time()
    if remaining<=0: raise ValueError('original deadline expired')
    actual=command or [sys.executable,str(Path(__file__).with_name('staged_child.py')),
        str((package/'bin/kpi-recovery-tn10').resolve()),str((assets/'target.json').resolve()),target_sha,str(output.resolve())]
    args=['/usr/bin/timeout','--signal=KILL',f'{remaining:.6f}s',*actual]
    result=run_phase(args,remaining,output/'aggregate',time.monotonic()+remaining,cuda,gpu['uuid'])
    atomic(output/'phase.json',result)
    if result['exitCode']!=0 or result['failure'] is not None:
        raise RuntimeError('stage failed; preserve candidate/partial results; no retry')
    return result
