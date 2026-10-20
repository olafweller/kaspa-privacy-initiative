"""Fixed sequential job INSIDE one externally watched process group.

All prover/compression/verification children inherit this group. This process
never starts a new session and never accepts a caller-selected command or case.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from common import atomic, sha
from recovery_package import BINS, CASES, check


def stages(package, output):
    producer=str((package/'bin'/BINS[0]).resolve())
    verifier=str((package/'bin'/BINS[1]).resolve())
    for case in CASES:
        proof=output/'proofs'/case
        yield case, 'prove', [producer,'prove',case,str((package/'inputs').resolve()),str(proof.resolve())]
        yield case, 'cpu-verify', [verifier,'verify-receipt',case,str((proof/'receipt.bin').resolve()),str((output/'cpu'/case).resolve())]
        if case in ('bob-exit','alice-exit'):
            yield case,'native-exit',[verifier,'verify-native-exit',case,str((proof/'receipt.bin').resolve()),str((output/'native'/case).resolve())]


def run(package, output, executor=None):
    assert 'RISC0_DEV_MODE' not in os.environ
    check(package)
    # The fixed Rust producer and verifier use create_dir, not create_dir_all.
    # Create their common parents once; children still require fresh leaf paths.
    (output/'proofs').mkdir()
    (output/'cpu').mkdir()
    (output/'stages').mkdir()
    (output/'native').mkdir()
    started=time.monotonic()
    records=[]
    for index,(case,kind,args) in enumerate(stages(package,output)):
        record={'case':case,'kind':kind,'startedUnix':time.time(),'startedMonotonic':time.monotonic(),
                'command':args,'sameProcessGroup':os.getpgrp(),'finished':False}
        path=output/'stages'/f'{index:02}-{case}-{kind}.json'
        atomic(path,record)
        # Used only by local synthetic orchestration tests. The production CLI
        # cannot inject an executor or a different target list.
        if executor is None:
            child=subprocess.Popen(args,stdin=subprocess.DEVNULL)
            record['pid']=child.pid;atomic(path,record)
            code=child.wait()
        else:code=executor(case,kind,args)
        record.update(finished=True,exitCode=code,finishedUnix=time.time(),finishedMonotonic=time.monotonic())
        atomic(path,record);records.append(record)
        atomic(output/'progress.json',{'stages':records,'lastCompleted':case+'-'+kind if code==0 else None})
        if code!=0:
            raise RuntimeError('fixed recovery stage failed: '+case+'-'+kind)
    receipts={case:sha((output/'proofs'/case/'receipt.bin').read_bytes()) for case in CASES}
    atomic(output/'pipeline-complete.json',{'scope':'SIX_LOCAL_RECOVERY_RECEIPTS_AND_BOTH_NATIVE_EXITS_NOT_TN10',
        'cases':list(CASES),'receipts':receipts,'seconds':time.monotonic()-started,
        'separateCpuVerificationProcesses':True,'bothGenuineNativeExitsChecked':True})
    return records


if __name__=='__main__':
    assert len(sys.argv)==3
    run(Path(sys.argv[1]),Path(sys.argv[2]))
