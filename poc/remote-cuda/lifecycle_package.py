"""Allowlisted public PR49 workload; independent executable expectations stay fixed."""
import json
import os
from pathlib import Path
import sys
from common import sha
from package import ROOT, checked_archive, write

SCOPE = 'FIXED_PRIVATE_NATIVE_FOUR_SUCCINCT_RECEIPTS'
IMAGE = '794cfff4cfa509799ec1f6750678d3fe4bc8623522aa647cc65e6b53955c4bc9'
CONTROL = '7a8f24092c34ed3eb81b3d0a0b796c588c615d3488ef9e61c21dbd1e4b83ea6e'
CUDA_SHA = '4447bbfa89b450611deda80825387d48cce6d23b428310ac45662f5c65f1cbcb'
PROOF_SHA = 'd9ee19513d2ba2b4296e0e9c4199c175ba2d0948b0f130d3df53a5e875415109'
CASES = ('deposit', 'credit-transfer', 'exit', 'reconcile')
BINS = ('kpi-private-native-producer', 'kpi-private-native-verifier')
INPUTS = {'guest.program.bin': '213ed12a0f0b514443fcab9608de5d42e0961fc6704fd51d49326106ead1e375', 'targets.json': '30770fe76a37d64bde1faa8a73d42ce1e081dc37027ef05fea1ebbc8fcf28521', 'deposit.input.bin': 'e2ee157504526738db3ba870f79590bbe655172fae72f850280b12df32f44f44', 'deposit.journal.bin': '82378ad35727f015951455e1dce5fb092b6180db0e2897d005ad768d09a789e7', 'credit-transfer.input.bin': 'c21a12cfdf2e462f2c7b7532756c13f21974807d8a71e015f2411e61681bc0b3', 'credit-transfer.journal.bin': '5bbc9e5f57b4e88d4a7840f3e6a8b1625f1a184fce88db28bb56652860279253', 'exit.input.bin': 'd3d4510e69efb00f09aaef779ecd7470bc00d5679ec1c99d377df43bfc222af4', 'exit.journal.bin': '57d751f4744d56e908b9673995e9df262dd01dd05913e0c21b1b02ff417dc964', 'reconcile.input.bin': '6329dcd51d26f94d26433f914c5c858bf004b9f6c2564e8c23bbeceaebbd87c6', 'reconcile.journal.bin': 'cc22d5a160148b6bad2cb105456257ba9093b7cb224b8c138c860c9efdbf99f6'}


def continuity(inputs):
    target = json.loads((inputs/'targets.json').read_text())
    assert target['expectedProgramImage'] == IMAGE
    assert target['expectedJoinControl'] == CONTROL
    assert list(target['batches']) == list(CASES), 'fixed batch list/order'
    previous = None
    for name in CASES:
        j = (inputs/(name+'.journal.bin')).read_bytes()
        b = target['batches'][name]
        assert len(j) == 352 and j.hex() == b['expectedJournalHex']
        assert sha(j) == b['expectedJournalSha256']
        assert sha((inputs/(name+'.input.bin')).read_bytes()) == b['inputSha256']
        assert b['segmentPo2'] == (16 if name in ('deposit', 'reconcile') else 20)
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
    policy = json.loads((package/'lifecycle-workload.json').read_text())
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
    reviewed = ROOT/'poc/private-native/evidence'
    bindings = json.loads((reviewed/'source-bindings.json').read_text())
    for name,h in bindings['sourceFiles'].items():
        assert sha((ROOT/name).read_bytes()) == h, 'reviewed source drift: '+name
    raw=binary.read_bytes()
    assert sha(raw) == PROOF_SHA
    out.mkdir(parents=True)
    for name,h in INPUTS.items():
        data=(reviewed/name).read_bytes();assert sha(data)==h
        write(out/'inputs'/name,data)
    for name in BINS:
        write(out/'bin'/name,raw);(out/'bin'/name).chmod(0o755)
    write(out/'lifecycle-workload.json',(json.dumps(policy_value(out),indent=2,sort_keys=True)+'\n').encode())
    return check(out)


def allowed():
    return {'lifecycle-workload.json'} | {'inputs/'+n for n in INPUTS} | {'bin/'+n for n in BINS}


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
    e=ROOT/'poc/private-native-proof/evidence'
    identity=json.loads((e/'package-identity.json').read_text())
    for name,h in identity['sourceFiles'].items():
        assert sha((ROOT/name).read_bytes()) == h, 'source/binary drift: '+name
    data=checked_archive(e/'public-package.tar.gz',identity['archive']['sha256'])
    assert set(data)==allowed()
    out.mkdir(parents=True)
    for name,raw in data.items():
        write(out/name,raw)
        if name.startswith('bin/'):(out/name).chmod(0o755)
    assert sha(data['lifecycle-workload.json']) == identity['policySha256']
    return check(out)


if __name__=='__main__':
    if sys.argv[1]=='restore':r=restore(Path(sys.argv[2]))
    elif sys.argv[1]=='build':r=build(Path(sys.argv[2]),Path(sys.argv[3]))
    else:raise SystemExit('build REVIEWED_BINARY NEW_PACKAGE | restore NEW_PACKAGE')
    print(json.dumps({'scope':r['scope'],'programImage':IMAGE,'cases':r['cases'],'proofStarted':False}))
