#!/usr/bin/env python3
"""Exercise the actual packaged wallet, no live user keys/network/proving."""
import json
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent
from build import build


def run(folder,*args,ok=True):
    r=subprocess.run([sys.executable,str(folder/'client.py'),*map(str,args)],capture_output=True,text=True,timeout=120)
    assert (r.returncode==0)==ok,(args,r.stdout,r.stderr)
    return r


def main(archive):
    identity=json.loads((HERE/'evidence/package-identity.json').read_text())
    assert archive.stat().st_size==identity['bytes'] and hashlib.sha256(archive.read_bytes()).hexdigest()==identity['sha256']
    with tempfile.TemporaryDirectory(prefix='kpi-start-kit-test-') as tmp:
        root=Path(tmp);package=root/'package'
        # This is our pinned build archive, not a generic user/GPU upload extractor.
        with zipfile.ZipFile(archive) as z:z.extractall(package)
        rebuilt=root/'rebuilt.zip'
        assert build(package/'bin/kpi-recovery-native-wallet',rebuilt)['sha256']==identity['sha256'],'source and distributed archive drift'
        run(package,'doctor')
        own=root/'user-owned'
        r=run(package,'init',own)
        assert set(p.name for p in (own/'public').iterdir())=={'alice-receive.json','bob-receive.json'}
        for role in ('alice','bob'):
            for n in ('wallet.backup','native.key'):
                assert (own/role/n).stat().st_mode&0o777==0o600
            data=json.loads((own/'public'/(role+'-receive.json')).read_text())
            assert set(data)=={'schema','domain','owner','incoming'}
            assert data==json.loads((own/role/'receive.json').read_text())
            assert (own/role).stat().st_mode&0o777==0o700
        run(package,'init',own,ok=False)
        public=run(package,'public',own).stdout
        assert 'nativePubkey' not in public and 'wallet.backup' not in public and 'native.key' not in public
        run(package,'init','/mnt/kpi-test-not-created',ok=False)
        receive=own/'bob/receive.json';receive.write_text(json.dumps(json.loads(receive.read_text())|{'nativePubkey':'00'*32}))
        run(package,'public',own,ok=False)
        receive.unlink();receive.symlink_to(own/'public/bob-receive.json')
        run(package,'public',own,ok=False)
        binary=package/'bin/kpi-recovery-native-wallet';raw=binary.read_bytes();binary.write_bytes(raw+b'corruption')
        run(package,'doctor',ok=False)
        binary.write_bytes(raw)
        fixture=package/'fixtures/deposit.input.bin';fixture.write_bytes(b'corruption')
        run(package,'doctor',ok=False)
    print(json.dumps({'scope':'ACTUAL_OFFLINE_START_KIT_TEST_NOT_TN10_OR_INDEPENDENT_USER_CUSTODY',
          'archiveHashAndReproducibleBuildVerified':True,'actualWalletAndSixBatchRebuildPassed':True,'freshTwoRoleInitPassed':True,
          'privateFilePermissionsChecked':True,'publicOnlyReceiveAllowlist':True,
          'overwriteMountedPathExtraReceiveFieldSymlinkBinaryAndFixtureTamperRejected':True,
          'newWalletProofs':0,'GPUJobs':0,'funding':False,'broadcast':False},indent=2))


if __name__=='__main__':main(Path(sys.argv[1]) if len(sys.argv)>1 else HERE/'KPI-wallet-start-linux-x86_64.zip')
