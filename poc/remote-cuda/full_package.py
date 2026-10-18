"""Build fixed public full-classifier inputs from the immutable PR39 archive."""
import json
from pathlib import Path
import sys

from package import ROOT, checked_archive, sha, write

ARCHIVE_SHA = 'eb39eb23d6dd7da2f55a45711fbcac2acaad844dee94e30e2a91d6f6705a1710'
IMAGE = '397bcdca688462b9573a4b55e3516e1a2511140512c53337eb54da0849a93716'
HOST_SHA = '3794fd416c903b1034801adcae647681c9442c67f963d3e2b2db915e50bde6d6'
CUDA_SHA = '4447bbfa89b450611deda80825387d48cce6d23b428310ac45662f5c65f1cbcb'


def build(out):
    source = ROOT/'poc/outer-proof-128m/evidence/local-outer-proof-artifacts.tar.gz'
    contents = checked_archive(source, ARCHIVE_SHA)
    manifest = json.loads((source.parent/'comparison.json').read_text())['archiveManifest']
    assert set(contents) == set(manifest)
    for name, data in contents.items():
        assert len(data) == manifest[name]['bytes'] and sha(data) == manifest[name]['sha256']
    out.mkdir(parents=True)
    inputs = {}
    for name, data in contents.items():
        target = None
        if name.startswith('local/expectations/'):
            target = name.removeprefix('local/')
        elif name.startswith('reused/fixtures-reviewed/'):
            target = 'fixtures/'+name.removeprefix('reused/fixtures-reviewed/')
        elif name in ['unchanged-classifier/classifier.program.bin', 'unchanged-classifier/identity.json']:
            target = 'programs/'+name.removeprefix('unchanged-classifier/')
        elif name.startswith('local/qualification/') and (name.endswith(('/report.json', '/journal.bin', '.resources.json', '/qualification.json'))):
            target = name.removeprefix('local/')
        if target:
            inputs[target] = {'sha256': sha(data), 'bytes': len(data)}
            write(out/'inputs'/target, data)
    expected = json.loads((out/'inputs/expectations/expectations.json').read_text())
    qualified = json.loads((out/'inputs/qualification/qualification.json').read_text())
    assert expected['expectedProgramImage'] == IMAGE and len(expected['cases']) == 24
    assert qualified['passed'] and len(qualified['cases']) == 24
    assert sha((out/'inputs/programs/classifier.program.bin').read_bytes()) == expected['programSha256']
    for case in expected['cases']:
        name = case['case']
        assert sha((out/'inputs/fixtures'/f'{name}.bin').read_bytes()) == case['inputSha256']
    policy = {'scope': 'FIXED_FULL_CLASSIFIER_ONE_SUCCINCT_RECEIPT',
              'referenceArchiveSha256': ARCHIVE_SHA, 'expectedProgramImage': IMAGE,
              'hostBinarySha256': HOST_SHA, 'cudaProverSha256': CUDA_SHA,
              'executionCycleLimit': 128000000, 'wholeProofJobSecondsLimit': 3600,
              'inputs': inputs}
    write(out/'full-workload.json', (json.dumps(policy, indent=2, sort_keys=True)+'\n').encode())
    print(json.dumps({'output': str(out), 'inputFiles': len(inputs),
                      'workloadSha256': sha((out/'full-workload.json').read_bytes())}))


if __name__ == '__main__':
    build(Path(sys.argv[1]))
