"""Single frozen private-note proof; existing service/guard and CUDA prover reused."""
import json
import os
from pathlib import Path
import shutil
import threading
import time

from common import atomic, sha
from private_package import SCOPE, IMAGE, CONTROL, INPUTS, CUDA_SHA, BINS, JOURNAL_SHA
from worker import hardware, run_phase, snapshot


def check_inputs(package, policy):
    assert policy['scope'] == SCOPE
    assert policy['expectedProgramImage'] == IMAGE and policy['expectedControlId'] == CONTROL
    assert policy['expectedHashfn'] == 'poseidon2' and policy['expectedJournalBytes'] == 352
    assert policy['expectedJournalSha256'] == JOURNAL_SHA
    assert policy['executionCycleLimit'] == 160000000 and policy['wholeProofJobSecondsLimit'] == 3600
    assert set(policy['inputs']) == set(INPUTS) and set(policy['binaries']) == set(BINS)
    for name, (_, expected_sha) in INPUTS.items():
        data = (package/'inputs'/name).read_bytes()
        spec = policy['inputs'][name]
        assert sha(data) == spec['sha256'] == expected_sha and len(data) == spec['bytes']
    for name in BINS:
        data = (package/'bin'/name).read_bytes()
        assert sha(data) == policy['binaries'][name]['sha256']
        assert len(data) == policy['binaries'][name]['bytes']
    assert policy['cudaProverSha256'] == CUDA_SHA
    assert sha(Path(os.environ['RISC0_SERVER_PATH']).read_bytes()) == CUDA_SHA


def execute(package, output, lease, update):
    started = time.monotonic()
    assert lease['stopUnix']-time.time() > 3660, 'full hour plus retrieval reserve required'
    deadline = started+min(3600, lease['stopUnix']-time.time()-60)
    policy = json.loads((package/'private-workload.json').read_text())
    check_inputs(package, policy)
    assert Path('/workspace').is_mount()
    output.mkdir()
    shutil.copytree(package/'inputs', output/'assets')
    gpu = hardware()
    atomic(output/'hardware.json', gpu | {'cudaProverSha256': CUDA_SHA,
           'producerSha256': policy['binaries'][BINS[0]]['sha256'],
           'workload': SCOPE, 'startupSeconds': time.monotonic()-started})
    proof = output/'proof'
    arguments = [str(package/'bin'/BINS[0]), 'prove', str(output/'assets'), str(proof)]
    update({'state': 'running', 'phase': 'private-note-proof', 'artifact': snapshot(output)})
    done = threading.Event()
    def checkpoint():
        while not done.wait(15):
            try:
                update({'state': 'running', 'phase': 'private-note-proof', 'artifact': snapshot(output)})
            except OSError:
                pass  # Absolute process/lease deadlines remain independent of backup.
    thread = threading.Thread(target=checkpoint, daemon=True)
    thread.start()
    try:
        report = run_phase(arguments, 3600, output/'full-proof', deadline, True, gpu['uuid'])
    finally:
        done.set()
        thread.join()
    update({'state': 'running', 'phase': 'proof-returned', 'artifact': snapshot(output)})
    assert report['exitCode'] == 0 and report['failure'] is None, 'private proof process failed'
    complete = json.loads((proof/'proof-complete.json').read_text())
    assert complete['scope'] == 'REAL_PRIVATE_NOTE_SUCCINCT_RECEIPT'
    assert complete['expectedProgramImage'] == IMAGE and complete['expectedControlId'] == CONTROL
    assert complete['noUnresolvedAssumptions'] and not complete['developmentMode']
    assert sha((proof/'classifier-receipt.bin').read_bytes()) == complete['receiptSha256']
    assert (proof/'classifier-journal.bin').read_bytes() == (output/'assets/expected-journal.bin').read_bytes()
    assert time.monotonic() < deadline, 'whole proof job exceeded limit'
    atomic(output/'complete.json', {'scope': 'ONE_PRIVATE_NOTE_RECEIPT_NOT_TN10_SETTLEMENT',
           'seconds': time.monotonic()-started, 'receiptSha256': complete['receiptSha256'],
           'cudaProcessActivityObserved': report['gpuProcessActivityObserved'],
           'independentCpuVerificationStillRequired': True})
    update({'state': 'completed', 'phase': 'done', 'artifact': snapshot(output)})
