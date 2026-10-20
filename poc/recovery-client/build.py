#!/usr/bin/env python3
"""Package only the existing reviewed public wallet binary and public fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'poc/remote-cuda'))
from recovery_package import CASES, INPUTS, IMAGE
WALLET_SHA='aeb84c7a3edd9b076e28c3035729fca9df0d582e44d33cbc951d697fb33c3c90'
PARAM_SHA='812b3bda0ec5f9b0c17fc1d530e49fc21defc9dcc5ea9c70a133ca62fec31e99'


def build(binary,destination):
    raw=binary.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==WALLET_SHA,'must reuse the PR56-reviewed wallet binary'
    pinned=json.loads((ROOT/'poc/recovery-native/runmanifest.json').read_text())
    assert pinned['walletExecutable']['sha256']==WALLET_SHA
    payload={'bin/kpi-recovery-native-wallet':raw}
    for name in ('client.py','START-HIER.txt'):
        payload[name]=(HERE/name).read_bytes()
    for name in ['targets.json',*(c+'.input.bin' for c in CASES)]:
        data=(ROOT/'poc/recovery-native/evidence/fixtures'/name).read_bytes()
        assert hashlib.sha256(data).hexdigest()==INPUTS[name]
        payload['fixtures/'+name]=data
    manifest={'schema':'KPI_LOCAL_RECOVERY_START_KIT_V1','scope':'OFFLINE_ONBOARDING_NOT_LIVE_TRIAL_READY',
              'platform':'linux-x86_64-glibc-2.34-plus','guestImage':IMAGE,
              'walletSha256':WALLET_SHA,'publicParametersSha256':PARAM_SHA,
              'publicParametersIncluded':False,'userWalletSecretsIncluded':False,
              'broadcast':False,'providerAccess':False,
              'walletSourceSha256':pinned['sourceSha256']['poc/recovery-native/host/src/bin/wallet.rs'],
              'files':{n:{'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()} for n,d in sorted(payload.items())}}
    payload['package.json']=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
    destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(payload.items()):
            item=zipfile.ZipInfo(name,date_time=(2026,10,20,0,0,0));item.create_system=3
            item.external_attr=(0o100755 if name.startswith('bin/') else 0o100644)<<16
            item.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(item,data)
    return {'filename':destination.name,'bytes':destination.stat().st_size,
            'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),**{k:v for k,v in manifest.items() if k!='files'}}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('binary',type=Path);p.add_argument('new_zip',type=Path);a=p.parse_args()
    print(json.dumps(build(a.binary,a.new_zip),indent=2))
