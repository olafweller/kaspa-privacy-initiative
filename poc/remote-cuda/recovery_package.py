"""Allowlisted public PR56 workload; independent executable expectations stay fixed."""
import json
import os
from pathlib import Path
import sys
from common import sha
from package import ROOT, checked_archive, write

SCOPE = 'FIXED_RECOVERY_SIX_SUCCINCT_RECEIPTS'
IMAGE = '095a2fb2f58c350ccd2688ae7f72748c915bd973c60fd4abaa8d87b282ad68b5'
CONTROL = '7a8f24092c34ed3eb81b3d0a0b796c588c615d3488ef9e61c21dbd1e4b83ea6e'
CUDA_SHA = '4447bbfa89b450611deda80825387d48cce6d23b428310ac45662f5c65f1cbcb'
PROOF_SHA = 'b90c13fea98b941a661e2d13ba8ddc96dc79418f2366c25ff4e53747f603ab9d'
CASES = ('deposit', 'credit-transfer', 'bob-exit', 'bob-reconcile', 'alice-exit', 'alice-reconcile')
BINS = ('kpi-recovery-producer', 'kpi-recovery-verifier')
INPUTS = {'guest.program.bin': '6039c3ef645d620bdd7eef6384750e73f51bcc8f9182aae1b1ac3c963601e75b', 'targets.json': 'c4f7a8f2ba37b4697c238331d14c2486b18df08f72ff0eb4bc2a948374e85b11', 'native-history.json': 'b3a39c5a2a9447a5301a03d9fb287598110a488cf6d04bb930408e6477bf1184', 'deposit.input.bin': '0697ed3e2ea9951c58b9d18956b7a906e304bba06242e6afbae0de4bd77ce49d', 'deposit.journal.bin': '501e2543326f1469c9e0dc199813c4755ccaced67ede5ae19cc6395cc88e0768', 'credit-transfer.input.bin': '0d122326fe6bee27cbb32f44a719f9c53ca317784924bfb9e445a627194f6df5', 'credit-transfer.journal.bin': 'adbe521187f9eb9a2b649904d135ee449dc71194372af69672fcdc6ffdbac71a', 'bob-exit.input.bin': '87eff1c4d151b87d9fcb7912088833fd8914aef4a04f4b0217bc4b24ae6e3211', 'bob-exit.journal.bin': '613f0f2fa9b7ce6ff14edb72975fa9ab3e7464dc98e90726df488740b37c59d4', 'bob-reconcile.input.bin': 'b45c6f49eb7c518a5708055308f9e1951201a17952a56142ccea0a81f9027937', 'bob-reconcile.journal.bin': '47657831b96c43aa7f5b378a403aae96cf0b41f73e8c059a07b2186babf0ce04', 'alice-exit.input.bin': '592756bd985230d6b68e19474013dce69c9b23e1fcd9e56f66e2a4b66b35cefb', 'alice-exit.journal.bin': 'fa432b0215e525b996d9fef2dcd54cde955f9d03a5c827b8ffbef973c5cf2c93', 'alice-reconcile.input.bin': 'a93f25645e05b99b19024611f1b3ea6fcc94a3062f644f385947b038d0baeb79', 'alice-reconcile.journal.bin': '7946024b771aeeb0b4227a1fc636e376bd797e5bf3d5cbfc2cfd0b9524bfbce0'}


def continuity(inputs):
    target = json.loads((inputs/'targets.json').read_text())
    assert target['expectedProgramImage'] == IMAGE
    assert target['expectedJoinControl'] == CONTROL
    assert set(target['batches']) == set(CASES), 'fixed batch list'
    previous = None
    for name in CASES:
        j = (inputs/(name+'.journal.bin')).read_bytes()
        b = target['batches'][name]
        assert len(j) == 352 and j.hex() == b['expectedJournalHex']
        assert sha(j) == b['expectedJournalSha256']
        assert sha((inputs/(name+'.input.bin')).read_bytes()) == b['inputSha256']
        assert b['segmentPo2'] == (16 if name == 'deposit' or name.endswith('reconcile') else 20)
        if previous is not None:
            assert previous[64:96] == j[:32], 'state root discontinuity'
            assert previous[96:128] == j[32:64], 'lane tip discontinuity'
            assert previous[160:256] == j[160:256], 'covenant/relation mismatch'
            assert previous[320:352] == j[320:352], 'lane mismatch'
        previous = j
    return target


def policy_value(package):
    return {'scope': SCOPE, 'expectedProgramImage': IMAGE, 'expectedJoinControl': CONTROL,
            'cases': list(CASES), 'executionCycleLimitPerBatch': 160000000,
            'aggregateProofProcessGroupSecondsLimit': 3600,
            'maxRentalSecondsFromActualCreation': 7200, 'spendPlanningLimitUsd': 5,
            'cudaProverSha256': CUDA_SHA,
            'inputs': {n: {'sha256': h, 'bytes': (package/'inputs'/n).stat().st_size} for n,h in INPUTS.items()},
            'binaries': {n: {'sha256': PROOF_SHA, 'bytes': (package/'bin'/n).stat().st_size} for n in BINS},
            'sameReviewedExecutableForProducerAndVerifier': True,
            'independentVerificationUsesSeparateProcesses': True,
            'walletSecretsIncluded': False, 'setupParametersIncluded': False,
            'rentalAuthorized': False, 'proofExecutionAuthorized': False,
            'TN10BroadcastAuthorized': False}


def check(package, cuda=False):
    policy = json.loads((package/'recovery-workload.json').read_text())
    assert policy == policy_value(package), 'fixed policy changed'
    for name,h in INPUTS.items():
        p=package/'inputs'/name
        assert not p.is_symlink() and sha(p.read_bytes()) == h, name
    for name in BINS:
        p=package/'bin'/name
        assert not p.is_symlink() and sha(p.read_bytes()) == PROOF_SHA, name
    continuity(package/'inputs')
    if cuda:
        assert sha(Path(os.environ['RISC0_SERVER_PATH']).read_bytes()) == CUDA_SHA
    return policy


def build(binary, out):
    reviewed = ROOT/'poc/recovery-native/evidence/fixtures'
    bindings = json.loads((ROOT/'poc/recovery-native/runmanifest.json').read_text())
    for name,h in bindings['sourceSha256'].items():
        assert sha((ROOT/name).read_bytes()) == h, 'reviewed source drift: '+name
    raw=binary.read_bytes()
    assert sha(raw) == PROOF_SHA
    out.mkdir(parents=True)
    for name,h in INPUTS.items():
        data=(reviewed/name).read_bytes();assert sha(data)==h
        write(out/'inputs'/name,data)
    for name in BINS:
        write(out/'bin'/name,raw);(out/'bin'/name).chmod(0o755)
    write(out/'recovery-workload.json',(json.dumps(policy_value(out),indent=2,sort_keys=True)+'\n').encode())
    return check(out)


def allowed():
    return {'recovery-workload.json'} | {'inputs/'+n for n in INPUTS} | {'bin/'+n for n in BINS}


def archive(package, destination):
    import gzip, io, tarfile
    assert {p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file()} == allowed()
    with destination.open('xb') as raw, gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as compressed, tarfile.open(fileobj=compressed,mode='w') as tar:
        for name in sorted(allowed()):
            p=package/name;assert not p.is_symlink();data=p.read_bytes()
            item=tarfile.TarInfo(name);item.size=len(data);item.mode=0o755 if name.startswith('bin/') else 0o644
            tar.addfile(item,io.BytesIO(data))
    return {'sha256':sha(destination.read_bytes()),'bytes':destination.stat().st_size}


def restore(out):
    e=ROOT/'poc/recovery-proof/evidence'
    identity=json.loads((e/'package-identity.json').read_text())
    for name,h in identity['sourceFiles'].items():
        assert sha((ROOT/name).read_bytes()) == h, 'source/binary drift: '+name
    data=checked_archive(e/'public-package.tar.gz',identity['archive']['sha256'])
    assert set(data)==allowed()
    out.mkdir(parents=True)
    for name,raw in data.items():
        write(out/name,raw)
        if name.startswith('bin/'):(out/name).chmod(0o755)
    assert sha(data['recovery-workload.json']) == identity['policySha256']
    return check(out)


if __name__=='__main__':
    if sys.argv[1]=='restore':r=restore(Path(sys.argv[2]))
    elif sys.argv[1]=='build':r=build(Path(sys.argv[2]),Path(sys.argv[3]))
    else:raise SystemExit('build REVIEWED_BINARY NEW_PACKAGE | restore NEW_PACKAGE')
    print(json.dumps({'scope':r['scope'],'programImage':IMAGE,'cases':r['cases'],'proofStarted':False}))
