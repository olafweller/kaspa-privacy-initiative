#!/usr/bin/env python3
"""Check retained source/base artifacts and neutral configuration; never prove or contact hosts."""
import hashlib,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'service'))
from staged_package import restore
from staged_policy import CASES,IMAGE,PROGRAM
from context import prepare

for n,h in json.loads((HERE/'evidence/source-bindings.json').read_text()).items():
    assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,n
m=json.loads((HERE/'runmanifest.json').read_text())
assert m['guestImage']==IMAGE and m['programSha256']==PROGRAM and m['batches']==list(CASES)
assert m['authorizations']=={'funding':False,'broadcast':False,'rental':False,'newOuterProof':False,'stopOriginalServices':False}
with tempfile.TemporaryDirectory() as d:
    d=Path(d);p=restore(d/'trusted');assert p['cases']==m['batches']
    prepare(d/'context')
    assert {f.relative_to(d/'context/base-dist').as_posix() for f in (d/'context/base-dist').rglob('*') if f.is_file()}=={'bin/kpi-recovery-tn10','guest.program.bin'}
print('Six-stage package, unchanged guest, pinned source/binary and trial-neutral image context verified. No RPC, rental, wallet proof, outer proof or broadcast.')
