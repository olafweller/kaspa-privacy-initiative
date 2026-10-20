"""Trusted local/B CPU verifier; never execute anything from GPU results."""
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
from common import atomic,sha
from package import write
from staged_archive import open_archive,read_compressed
from recovery_package import BINS, CASES, INPUTS, check

MAX_ARCHIVE = 64*1024**2
MAX_ARCHIVE_TAR = 256*1024**2
MAX_MEMBERS = 512
MAX_FILE = 32*1024**2
MAX_CONTENT = 128*1024**2


def extract(archive, out, expected_sha):
    # Include hidden extension records and padding in the expansion bound,
    # before tarfile can process PAX/GNU metadata. The digest is not a size cap.
    data=read_compressed(archive,MAX_ARCHIVE)
    assert sha(data)==expected_sha, 'archive hash mismatch'
    content={};total=0
    with open_archive(data,MAX_ARCHIVE,MAX_ARCHIVE_TAR,MAX_MEMBERS) as (tar,members):
        for item in members:
            name=PurePosixPath(item.name)
            assert name.parts and len(item.name)<=240
            assert item.isfile() and not name.is_absolute() and '..' not in name.parts
            assert str(name)==item.name and item.name not in content
            assert 0<=item.size<=MAX_FILE
            total+=item.size
            assert total<=MAX_CONTENT
            raw=tar.extractfile(item).read()
            assert len(raw)==item.size
            content[item.name]=raw
    # Reject malformed/oversized archives before creating any output directory.
    out.mkdir()
    for name,raw in content.items():write(out/name,raw)
    return {'safeRegularFilesExtracted':len(content)}


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
    native={}
    (out/'native').mkdir()
    for case in ('bob-exit','alice-exit'):
        if case not in results:continue
        receipt=downloaded/'proofs'/case/('candidate-receipt.bin' if results[case]['candidateOnly'] else 'receipt.bin')
        args=[verifier,'verify-native-exit',case,str(receipt),str((out/'native'/case).resolve())]
        try:
            if executor is None:subprocess.run(args,env=env,stdin=subprocess.DEVNULL,check=True,timeout=120)
            else:executor(args)
            native[case]=True
        except subprocess.SubprocessError as error:failures[case+'-native']=type(error).__name__
    result={'scope':'INDEPENDENT_CPU_SIX_RECOVERY_RECEIPTS_NOT_TN10',
            'verifiedReceipts':results,'failures':failures,'verifiedCount':len(results),
            'nativePermissionAndRestrictedPayoutVerified':native,
            'allSixCryptographicallyVerified':len(results)==6 and len(native)==2 and not failures,
            'allSixFinalReceiptsVerified':len(results)==6 and len(native)==2 and not failures and not any(r['candidateOnly'] for r in results.values()),
            'CUDAQualificationRequiresSeparateTelemetry':True,'actualTN10Broadcast':False}
    atomic(out/'verification.json',result)
    return result


if __name__=='__main__':
    if len(sys.argv)==5 and sys.argv[1]=='extract':
        print(json.dumps(extract(Path(sys.argv[2]),Path(sys.argv[3]),sys.argv[4])));raise SystemExit(0)
    assert len(sys.argv)==5 and sys.argv[1]=='verify'
    r=verify(*(Path(x) for x in sys.argv[2:]));print(json.dumps(r,indent=2))
    # Partial results survive, but partial/failing output is never full success.
    raise SystemExit(0 if r['allSixFinalReceiptsVerified'] else 1)
