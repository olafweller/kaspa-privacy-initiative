"""Records process-group identity before running the reviewed fixed child path."""
import json
import os
from pathlib import Path
import sys
import time
from staged_policy import reviewed


def identity(group):
    fields=Path(f'/proc/{group}/stat').read_text().rsplit(')',1)[1].split()
    return {'group':group,'startTicks':fields[19],
            'bootId':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}


def gate(output,digest):
    volume=output.parents[2]
    state=json.loads((volume/'state.json').read_text())
    ledger=json.loads((volume/'ledger.json').read_text())
    assert state['state']=='running' and state['currentStage']==output.name
    assert state['received'][output.name]['targetSha256']==digest
    assert ledger['attempted'][-1]==output.name and time.time()<ledger['deadlineUnix']


if __name__=='__main__':
    assert len(sys.argv)==5 and 'RISC0_DEV_MODE' not in os.environ
    output=Path(sys.argv[4]);assert output.is_dir()
    reviewed.atomic(output/'supervision.json',identity(os.getpgrp()))
    gate(output,sys.argv[3])
    reviewed.child(sys.argv[1],sys.argv[2],sys.argv[3],output)
