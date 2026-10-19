"""B verifies returned bytes with trusted local targets and executable only."""
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
from common import atomic,sha
from staged_policy import CASES,check,write


def verify(package,archive,targets,out):
    check(package);expected=json.loads(targets.read_text());out.mkdir()
    candidates={}
    with tarfile.open(fileobj=io.BytesIO(archive.read_bytes()),mode='r:gz') as tar:
        seen=set();total=0
        for item in tar:
            total+=item.size
            if item.size<0 or item.size>64*1024**2 or total>256*1024**2:raise ValueError('bounded evidence archive required')
            if item.name in seen:raise ValueError('duplicate archive member')
            seen.add(item.name)
            for stage in CASES:
                if item.name in (f'stages/{stage}/proof/receipt.bin',f'stages/{stage}/proof/candidate-receipt.bin'):
                    assert item.isfile() and 0<item.size<=24*1024**2
                    raw=tar.extractfile(item).read()
                    # Prefer the final receipt if both candidate and final exist.
                    if stage not in candidates or item.name.endswith('/receipt.bin'):candidates[stage]=raw
    (out/'receipts').mkdir();(out/'cpu').mkdir();results={}
    for stage in CASES:
        if stage not in candidates:continue
        e=expected[stage];target=Path(e['targetPath'])
        assert sha(target.read_bytes())==e['targetSha256'],'independent B target mismatch'
        receipt=out/'receipts'/(stage+'.bin');write(receipt,candidates[stage])
        args=[str((package/'bin/kpi-private-native-tn10').resolve()),'verify',str(target.resolve()),e['targetSha256'],str(receipt.resolve()),str((out/'cpu'/stage).resolve())]
        with (out/(stage+'.stdout.log')).open('xb') as log,(out/(stage+'.stderr.log')).open('xb') as err:
            result=subprocess.run(args,stdout=log,stderr=err,timeout=120)
        results[stage]={'receiptSha256':sha(candidates[stage]),'targetSha256':e['targetSha256'],'verified':result.returncode==0}
    report={'scope':'TRUSTED_B_CPU_VERIFICATION_NOT_LIVE_NATIVE_ACCEPTANCE','results':results,
            'verifiedCount':sum(x['verified'] for x in results.values()),
            'allFourVerified':len(results)==4 and all(x['verified'] for x in results.values()),
            'independentImplementations':False,'downloadedExecutablesRun':False}
    atomic(out/'verification.json',report);return report


if __name__=='__main__':
    assert len(sys.argv)==5
    print(json.dumps(verify(*map(Path,sys.argv[1:])),indent=2))
