"""Exactly one aggregate 3600-second process group for ALL four proof batches."""
import json
import os
from pathlib import Path
import shutil
import threading
import time
from common import atomic
from lifecycle_package import SCOPE, CASES, check
from worker import hardware, run_phase, snapshot


def cuda_by_batch(output):
    start=json.loads((output/'aggregate.started.json').read_text())['unixSeconds']
    samples=[json.loads(s) for s in (output/'aggregate.samples.jsonl').read_text().splitlines()]
    result={}
    for p in sorted((output/'stages').glob('*-prove.json')):
        stage=json.loads(p.read_text())
        if not stage.get('finished') or stage.get('exitCode')!=0:continue
        matching=[s for s in samples if stage['startedUnix']<=start+s['seconds']<=stage['finishedUnix']]
        observed=any(s['matchingGpuProcesses'] and (s['gpuDeviceUtilizationPercent'] or 0)>0 for s in matching)
        result[stage['case']]={'matchingProcessCudaActivityObserved':observed,'sampleCount':len(matching),
            'peakSampledGroupRssBytes':max((s['summedRssBytes'] for s in matching),default=0),
            'peakMatchingGpuVramMiB':max((sum(p['vramMiB'] for p in s['matchingGpuProcesses']) for s in matching),default=0),
            'seconds':stage['finishedMonotonic']-stage['startedMonotonic']}
    return result


def execute(package, output, lease, update):
    started=time.monotonic()
    assert lease['stopUnix']-time.time()>3660, 'full aggregate hour and retrieval reserve required'
    deadline=started+3600  # Never reset for another batch, compression or CPU checks.
    policy=check(package,cuda=True)
    assert Path('/workspace').is_mount()
    output.mkdir()
    shutil.copytree(package/'inputs',output/'assets')
    gpu=hardware()
    atomic(output/'hardware.json',gpu|{'scope':SCOPE,'cudaProverSha256':policy['cudaProverSha256'],
           'startupSeconds':time.monotonic()-started,'aggregateExternalWatchdog':'GNU timeout --signal=KILL; same process group; survives service death'})
    done=threading.Event()
    def checkpoint():
        while not done.wait(15):
            try:update({'state':'running','phase':'four-batch-aggregate','artifact':snapshot(output)})
            except OSError:pass  # Independent process timer and B lease deadline keep running.
    thread=threading.Thread(target=checkpoint,daemon=True);thread.start()
    try:
        update({'state':'running','phase':'four-batch-aggregate','artifact':snapshot(output)})
        # One external run_phase timer watches the entire runner process group,
        # including all sequential prover, compression, CPU and native children.
        arguments=['/usr/bin/timeout','--signal=KILL',f'{max(0,deadline-time.monotonic()):.6f}s',
                   os.sys.executable,str(Path(__file__).with_name('lifecycle_runner.py')),str(package),str(output)]
        report=run_phase(arguments,
                         3600,output/'aggregate',deadline,True,gpu['uuid'])
    finally:
        done.set();thread.join()
    update({'state':'running','phase':'aggregate-returned','artifact':snapshot(output)})
    assert report['exitCode']==0 and report['failure'] is None, 'aggregate proof/check process failed'
    complete=json.loads((output/'pipeline-complete.json').read_text())
    assert complete['cases']==list(CASES)
    batches=cuda_by_batch(output)
    atomic(output/'cuda-by-batch.json',batches)
    assert set(batches)==set(CASES) and all(r['matchingProcessCudaActivityObserved'] for r in batches.values()), 'per-batch CUDA activity not established'
    assert time.monotonic()<deadline, 'aggregate proof/check deadline exceeded'
    atomic(output/'complete.json',{'scope':SCOPE,'seconds':time.monotonic()-started,
           'fourReceiptsAndNativeExitChecked':True,'independentBVerificationStillRequired':True,
           'CUDAProcessActivityObservedForAllBatches':True,'actualTN10Broadcast':False})
    update({'state':'completed','phase':'done','artifact':snapshot(output)})
