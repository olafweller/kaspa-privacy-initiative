"""Reverify retained actual-input receipts on trusted CPU. No network or proving."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'poc/remote-cuda'))
from staged_package import restore
from staged_policy import unpack,CASES
from staged_archive import open_archive

def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    evidence=HERE/'evidence'
    manifest=json.loads((evidence/'manifest.json').read_text())
    for name,record in manifest['files'].items():
        path=evidence/name
        assert path.is_file() and not path.is_symlink()
        assert path.stat().st_size==record['bytes'] and sha(path.read_bytes())==record['sha256'],name
    result=json.loads((evidence/'result.json').read_text())
    assert result['actualTN10LifecycleCompleted'] and result['receiptCount']==4
    assert result['singleGpuAttempt'] and result['aggregateElapsedSeconds']<=3600
    assert result['providerStoppedAndDeleted'] and result['native']['finalAccounting']['unpaid_exits']==0
    assert result['native']['finalAccounting']['private_liability']==result['native']['finalAccounting']['reserve_principal']==600_000_000
    assert result['native']['bobPrincipalSompi']==400_000_000 and result['native']['bobRentRefundSompi']==50_000_000
    captures=json.loads((evidence/'native/capture-identities.json').read_text())
    for case,capture in captures.items():
        digest=hashlib.sha256();size=0
        with gzip.open(evidence/capture['path'],'rb') as source:
            for chunk in iter(lambda:source.read(1024*1024),b''):
                digest.update(chunk);size+=len(chunk)
        assert digest.hexdigest()==capture['rawSha256'] and size==capture['rawBytes']
        if case in CASES:assert capture['rawSha256']==result['targets'][case]['captureSha256']
    previous=None
    with tempfile.TemporaryDirectory() as temporary:
        work=Path(temporary);package=work/'trusted';policy=restore(package)
        for case in CASES:
            expected=result['targets'][case]
            target=evidence/case/'target.json'
            assert sha(target.read_bytes())==expected['targetSha256']
            assets,t=unpack((evidence/case/'public.tar.gz').read_bytes(),expected['targetSha256'],policy,case)
            journal=bytes.fromhex(t['journalHex'])
            if previous:
                assert journal[:64]==previous[64:128] and journal[160:256]==previous[160:256] and journal[320:]==previous[320:]
            previous=journal
            receipt=evidence/'receipts'/(case+'.bin')
            assert sha(receipt.read_bytes())==expected['receiptSha256']
            output=work/case
            subprocess.run([str(package/'bin/kpi-private-native-tn10'),'verify',str(target),expected['targetSha256'],str(receipt),str(output)],check=True)
            controls=json.loads((output/'verification.json').read_text())['negativeControls']
            assert controls['tamperedJournalOffsetsRejected']==list(range(0,352,32))
            assert all(controls[k] for k in ['wrongImageRejected','corruptedSealRejected','malformedControlInclusionRejected','wrongExpectedControlRejectedBySealVerifier'])
    data=(evidence/'gpu/terminal-artifacts.tar.gz').read_bytes()
    assert sha(data)==result['gpuArchiveSha256']
    with open_archive(data,64*1024**2,256*1024**2,2048) as (tar,members):
        entries=list(members);names={m.name:m for m in entries};assert len(names)==len(entries)
        load=lambda n:json.loads(tar.extractfile(names[n]).read())
        state=load('service-state.json');ledger=load('ledger.json')
        assert state['state']=='completed' and ledger['attempted']==ledger['completed']==list(CASES)
        start=ledger['deadlineUnix']-3600
        for case in CASES:
            prefix='stages/'+case+'/'
            assert sha(tar.extractfile(names[prefix+'proof/receipt.bin']).read())==result['targets'][case]['receiptSha256']
            phase=load(prefix+'phase.json');hardware=load(prefix+'hardware.json');stats=load(prefix+'proof/stats.json')
            assert hardware['name']=='NVIDIA L40S' and hardware['computeCapability']=='8.9' and hardware['vramMiB']>=45000
            assert phase['exitCode']==0 and phase['failure'] is None and phase['gpuProcessActivityObserved']
            assert stats['user_cycles']<=160_000_000 and stats==result['stats'][case]
            assert load(prefix+'aggregate.started.json')['unixSeconds']+phase['wallSeconds']<=ledger['deadlineUnix']
            samples=tar.extractfile(names[prefix+'aggregate.samples.jsonl'])
            seen=False
            for line in samples:
                sample=json.loads(line)
                for gpu in sample['matchingGpuProcesses']:
                    assert gpu['pid'] in sample['groupPids'] and gpu['gpuUuid']==hardware['uuid']
                    if sample['gpuDeviceUtilizationPercent']>0:seen=True
            assert seen,case
    for attack in ['underpay','reserve','recipient','replay']:
        rejected=json.loads((evidence/'native'/('payout-'+attack+'-rejected.json')).read_text())
        reason=rejected['reason'].lower()
        assert ('script ran, but verification failed' in reason) if attack!='replay' else ('orphan' in reason)
    stop=json.loads((evidence/'gpu/provider-stop-readback.json').read_text())
    deleted=json.loads((evidence/'gpu/provider-deletion.json').read_text())
    assert stop['providerDesiredExitedConfirmed'] and stop['guardStop']['providerDesiredExitedConfirmed']
    assert deleted['providerGetStatus']==404 and deleted['podAbsentFromList']
    print('PASS: four actual-input real receipts, full connected journals, 60 cryptographic negatives, CUDA samples, native rejection records and provider cleanup evidence. No new proof, RPC or provider action.')

if __name__=='__main__':main()
