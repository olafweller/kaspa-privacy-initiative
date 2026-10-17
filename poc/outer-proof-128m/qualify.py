#!/usr/bin/env python3
"""Execute all existing full and narrow cases before the single proof attempt."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

programs, fixtures, setup, expectations, output = map(Path, sys.argv[1:])
output.mkdir()
e = json.loads((expectations / 'expectations.json').read_text())
assert e['executionCycleLimit'] == 128_000_000
assert e['expectedProgramImage'] == '397bcdca688462b9573a4b55e3516e1a2511140512c53337eb54da0849a93716'
# Read byte equality against the already published PR38 archive before running.
with tarfile.open('poc/accelerated-bn254/evidence/local-backend-artifacts.tar.gz', 'r:gz') as archive:
    for name in ['classifier.program.bin', 'classifier.raw.elf', 'identity.json']:
        assert archive.extractfile('local/programs-final/' + name).read() == (programs / name).read_bytes()
    for case in e['cases']:
        name = case['case'] + '.bin'
        data = (fixtures / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == case['inputSha256']
        assert archive.extractfile('reused-pr37/fixtures-reviewed/' + name).read() == data
    for name in ['vk.bin', 'pvk.bin', 'pvk-uncompressed.bin']:
        assert archive.extractfile('reused-pr37/setup-01/' + name).read() == (setup / name).read_bytes()

results = []
try:
    for case in e['cases']:
        label = case['case']
        result = output / ('result-' + label)
        command = ['python3', 'poc/outer-proof-128m/run_resources.py', '900',
                   str(output / ('measure-' + label)),
                   '.local/ci-target/release/kpi-takeover-host', 'accelerated-bn254',
                   'profile', str(programs), str(fixtures), str(setup), str(result),
                   label, 'approved-128m']
        run = subprocess.run(command, check=False, timeout=930)
        assert run.returncode == 0, f'{label}: process/resource failure'
        resource = json.loads((output / ('measure-' + label + '.resources.json')).read_text())
        assert resource['exitCode'] == 0 and resource['limitExceeded'] is None
        report = json.loads((result / 'report.json').read_text())
        assert report['cycleBudget'] == 128_000_000 and report['profile'] == 'approved-128m'
        assert report['expectedProgramImage'] == e['expectedProgramImage']
        if case['authenticationControl']:
            assert report['expectedAuthenticationFailureConfirmed'] is True
        else:
            assert report['completed'] is True and report['userCycles'] <= 128_000_000
            journal = (result / 'journal.bin').read_bytes()
            assert journal == (expectations / (label + '-expected-journal.bin')).read_bytes()
            assert hashlib.sha256(journal).hexdigest() == case['journalSha256']
        results.append({'case': label, 'report': report, 'resource': resource})
        print(label, 'PASS', report.get('outcomes', 'specific authentication abort'), flush=True)
except BaseException as error:
    (output / 'qualification.json').write_text(json.dumps({
        'passed': False, 'cases': results, 'failure': repr(error)}, indent=2) + '\n')
    raise
(output / 'qualification.json').write_text(json.dumps({
    'scope': 'APPROVED_128M_FULL_EXECUTION_QUALIFICATION_NOT_PROOF',
    'passed': True, 'cases': results, 'programAndInputsMatchPublishedPr38Archive': True,
    'expectedProgramImage': e['expectedProgramImage']}, indent=2) + '\n')
