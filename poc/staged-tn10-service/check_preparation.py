"""Check the supplemental preparation without GPU, chain or provider calls."""
import hashlib
import json
from pathlib import Path

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]


def check():
    load=lambda n:json.loads((BASE/n).read_text())
    manifest=load('runmanifest.json');deploy=load('deployment.json');q=load('evidence/qualification.json')
    assert not any(manifest['authorizations'].values())
    assert manifest['limits']['aggregateSeconds']==3600 and manifest['limits']['rentalSecondsFromActualCreation']==7200
    assert manifest['limits']['attempts']==1 and not manifest['limits']['automaticRetries']
    assert [x['name'] for x in manifest['stages']]==['deposit','credit-transfer','exit','reconcile']
    assert all(x['targetSha256'] is None and x['receiptSha256'] is None for x in manifest['stages'])
    assert not any(q[k] for k in ['actualProviderCalled','actualProviderStopTested','actualCudaExecuted','newProofJobStarted','liveTN10Called','fundingOrBroadcast'])
    for name,digest in load('evidence/source-sha256.json').items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    if not deploy['publicationPending']:
        assert '@sha256:' in deploy['immutableImage']
        assert manifest['stagedImageDigest']==deploy['immutableImage'] and not q['publishedImagePending']
        smoke=load('evidence/published-image-smoke.json')
        assert not smoke['proofJobStarted'] and not smoke['providerCalled'] and not smoke['cudaExecutionQualified']
        assert len(smoke['retainedCpuReceiptChecks'])==4
    print('Staged preparation bindings valid; live release remains absent.')


if __name__=='__main__':check()
