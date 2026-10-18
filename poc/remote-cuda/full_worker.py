"""One fixed full-classifier proof, using the already qualified CUDA binary."""
import json
import os
from pathlib import Path
import shutil
import threading
import time

from common import atomic, sha
from worker import hardware, run_phase, snapshot


def check_inputs(package, policy):
    assert policy['scope'] == 'FIXED_FULL_CLASSIFIER_ONE_SUCCINCT_RECEIPT'
    assert policy['executionCycleLimit'] == 128000000 and policy['wholeProofJobSecondsLimit'] == 3600
    for name, spec in policy['inputs'].items():
        data = (package/'inputs'/name).read_bytes()
        assert len(data) == spec['bytes'] and sha(data) == spec['sha256']
    host = Path('/opt/kpi/package/bin/kpi-takeover-host')
    assert sha(host.read_bytes()) == policy['hostBinarySha256']
    assert sha(Path(os.environ['RISC0_SERVER_PATH']).read_bytes()) == policy['cudaProverSha256']


def execute(package, output, lease, update):
    started = time.monotonic()
    deadline = started+min(3600, lease['stopUnix']-time.time()-60)
    assert deadline > started
    policy = json.loads((package/'full-workload.json').read_text())
    check_inputs(package, policy)
    assert Path('/workspace').is_mount()
    output.mkdir()
    shutil.copytree(package/'inputs', output/'assets')
    gpu = hardware()
    atomic(output/'hardware.json', gpu | {'cudaProverSha256': policy['cudaProverSha256'],
           'hostBinarySha256': policy['hostBinarySha256'], 'workload': policy['scope'],
           'startupSeconds': time.monotonic()-started})
    host = '/opt/kpi/package/bin/kpi-takeover-host'
    inputs = output/'assets'
    proof = output/'proof'
    arguments = [host, 'outer-proof-128m', 'prove', str(inputs/'programs'),
                 str(inputs/'fixtures'), str(inputs/'expectations'),
                 str(inputs/'qualification'), str(proof)]
    update({'state': 'running', 'phase': 'full-classifier-proof', 'artifact': snapshot(output)})
    done = threading.Event()
    def checkpoint():
        while not done.wait(15):
            try:
                update({'state': 'running', 'phase': 'full-classifier-proof', 'artifact': snapshot(output)})
            except OSError:
                pass  # Backup failure must not change the independent deadlines.
    thread = threading.Thread(target=checkpoint, daemon=True)
    thread.start()
    try:
        report = run_phase(arguments, 3600, output/'full-proof', deadline, True, gpu['uuid'])
    finally:
        done.set()
        thread.join()
    update({'state': 'running', 'phase': 'full-proof-returned', 'artifact': snapshot(output)})
    assert report['exitCode'] == 0 and report['failure'] is None, 'full proof process failed'
    complete = json.loads((proof/'proof-complete.json').read_text())
    assert complete['scope'] == 'REAL_SUCCINCT_CLASSIFIER_RECEIPT'
    assert complete['expectedProgramImage'] == policy['expectedProgramImage']
    assert complete['noUnresolvedAssumptions'] and not complete['developmentMode']
    assert sha((proof/'classifier-receipt.bin').read_bytes()) == complete['receiptSha256']
    assert (proof/'classifier-journal.bin').read_bytes() == (inputs/'expectations/expected-journal.bin').read_bytes()
    assert time.monotonic() < deadline, 'whole proof job exceeded declared limit'
    atomic(output/'complete.json', {'scope': 'ONE_COMPLETE_CLASSIFIER_RECEIPT_NOT_TN10_SETTLEMENT',
           'seconds': time.monotonic()-started, 'receiptSha256': complete['receiptSha256'],
           'cudaProcessActivityObserved': report['gpuProcessActivityObserved'],
           'independentCpuVerificationStillRequired': True})
    update({'state': 'completed', 'phase': 'done', 'artifact': snapshot(output)})
