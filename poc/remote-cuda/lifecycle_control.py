"""Trusted local/B CPU verifier; never execute anything from GPU results."""
import json
import os
from pathlib import Path
import subprocess
import sys
from common import atomic,sha
from package import checked_archive,write
from lifecycle_package import BINS, CASES, INPUTS, check


def verify(package, downloaded, out, executor=None):
    check(package)
    downloaded=downloaded.resolve()
    for name,h in INPUTS.items():
        p=downloaded/'assets'/name
        assert p.resolve().is_relative_to(downloaded) and not p.is_symlink()
        assert sha(p.read_bytes())==h, 'returned public input mismatch'
    out.mkdir()
    # No network/service/provider secrets or development mode enter verification.
    env={k:os.environ[k] for k in ('PATH','HOME','LD_LIBRARY_PATH') if k in os.environ}
    verifier=str((package/'bin'/BINS[1]).resolve())
    results={};failures={}
    for case in CASES:
        folder=downloaded/'proofs'/case
        receipt=folder/'receipt.bin'
        if not receipt.exists():receipt=folder/'candidate-receipt.bin'
        if not receipt.exists():continue
        assert receipt.resolve().is_relative_to(downloaded) and not receipt.is_symlink()
        args=[verifier,'verify-receipt',case,str(receipt),str((out/case).resolve())]
        try:
            if executor is None:subprocess.run(args,env=env,stdin=subprocess.DEVNULL,check=True,timeout=120)
            else:executor(args)
            results[case]={'sha256':sha(receipt.read_bytes()),'candidateOnly':receipt.name=='candidate-receipt.bin'}
        except subprocess.SubprocessError as error:
            failures[case]=type(error).__name__
    native=False
    if 'exit' in results:
        receipt=downloaded/'proofs/exit'/('candidate-receipt.bin' if results['exit']['candidateOnly'] else 'receipt.bin')
        args=[verifier,'verify-native-exit',str(receipt),str((out/'native-exit').resolve())]
        try:
            if executor is None:subprocess.run(args,env=env,stdin=subprocess.DEVNULL,check=True,timeout=120)
            else:executor(args)
            native=True
        except subprocess.SubprocessError as error:failures['native-exit']=type(error).__name__
    result={'scope':'INDEPENDENT_CPU_FOUR_LIFECYCLE_RECEIPTS_NOT_TN10',
            'verifiedReceipts':results,'failures':failures,'verifiedCount':len(results),
            'nativePermissionAndRestrictedPayoutVerified':native,
            'allFourCryptographicallyVerified':len(results)==4 and native and not failures,
            'CUDAQualificationRequiresSeparateTelemetry':True,'actualTN10Broadcast':False}
    atomic(out/'verification.json',result)
    return result


if __name__=='__main__':
    if len(sys.argv)==5 and sys.argv[1]=='extract':
        content=checked_archive(Path(sys.argv[2]),sys.argv[4]);out=Path(sys.argv[3]);out.mkdir()
        for name,raw in content.items():write(out/name,raw)
        print(json.dumps({'safeRegularFilesExtracted':len(content)}));raise SystemExit(0)
    assert len(sys.argv)==5 and sys.argv[1]=='verify'
    r=verify(*(Path(x) for x in sys.argv[2:]));print(json.dumps(r,indent=2))
    # Partial results survive, but partial/failing output is never full success.
    raise SystemExit(0 if r['allFourCryptographicallyVerified'] else 1)
