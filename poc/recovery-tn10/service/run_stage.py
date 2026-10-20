"""Future staged GPU entry point, NOT invoked during preparation.

Six targets cannot be frozen before chain acceptance of preceding settlements.
Each arrives separately from the trusted controller. One persistent deadline
starts at the first proof and also counts intervening chain/proof waits. The
unchanged B guard is still responsible for the independent rental deadline.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

CASES = ('deposit','credit-transfer','bob-exit','bob-reconcile','alice-exit','alice-reconcile')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic(path, value):
    tmp = path.with_suffix('.tmp')
    with tmp.open('w', encoding='utf8') as f:
        json.dump(value, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def lease_identity(lease):
    return {k: lease[k] for k in ('podId', 'createdUnix', 'stopUnix')}


def reserve(ledger, target, target_sha, lease, now):
    if not 0 < lease['stopUnix'] - lease['createdUnix'] <= 7200 or now < lease['createdUnix']:
        raise ValueError('lease exceeds two hours from actual creation')
    if now >= lease['stopUnix'] - 300:
        raise ValueError('insufficient retrieval margin')
    if ledger is None:
        if lease['stopUnix'] - now <= 3960:
            raise ValueError('need full shared hour plus six-minute transfer/stop margin')
        ledger = {'trial': target['trial'], 'deadlineUnix': now+3600,
                  'leaseSha256': hashlib.sha256(json.dumps(lease_identity(lease), sort_keys=True).encode()).hexdigest(),
                  'attempted': [], 'completed': []}
    if ledger['leaseSha256'] != hashlib.sha256(json.dumps(lease_identity(lease), sort_keys=True).encode()).hexdigest():
        raise ValueError('lease changed; no extension')
    if now >= ledger['deadlineUnix']:
        raise ValueError('original aggregate deadline expired')
    index = len(ledger['attempted'])
    if (ledger['trial'] != target['trial'] or index >= len(CASES) or
            target['stage'] != CASES[index] or ledger['completed'] != list(CASES[:index])):
        raise ValueError('wrong order, failed attempt, duplicate or different trial')
    journal = bytes.fromhex(target['journalHex'])
    if len(journal) != 352:
        raise ValueError('complete journal required')
    if index:
        previous = bytes.fromhex(ledger['lastJournalHex'])
        if journal[:64] != previous[64:128] or journal[160:256] != previous[160:256] or journal[320:] != previous[320:]:
            raise ValueError('state/tip/protocol/lane discontinuity')
    ledger['attempted'].append(target['stage'])
    ledger['lastTargetSha256'] = target_sha
    ledger['pendingJournalHex'] = target['journalHex']
    return ledger


def child(binary, target, target_sha, output):
    # Called only under the external GNU timeout. Children inherit its process
    # group. CPU verification is a distinct invocation of the trusted binary.
    os.environ['KPI_TN10_EXTERNAL_DEADLINE'] = '3600'
    subprocess.run([binary, 'prove', target, target_sha, str(output/'proof')], check=True)
    subprocess.run([binary, 'verify', target, target_sha, str(output/'proof/receipt.bin'), str(output/'cpu')], check=True)


def run(state_dir, lease_path, target_path, expected, binary, binary_sha, output):
    state_dir, output = Path(state_dir), Path(output)
    if 'RISC0_DEV_MODE' in os.environ or sha(binary) != binary_sha or sha(target_path) != expected:
        raise ValueError('trusted binaries/targets and real mode required')
    target = json.loads(Path(target_path).read_text())
    lease = json.loads(Path(lease_path).read_text())
    # Service preflight is supplied by trusted B, not GPU-returned metadata.
    if lease['workloadScope'] != 'STAGED_RECOVERY_TN10_SIX_V1' or not 0 <= time.time()-lease['guardHeartbeatUnix'] < 30:
        raise ValueError('independent B lease/heartbeat preflight required')
    if os.environ.get('RUNPOD_POD_ID') != lease['podId']:
        raise ValueError('lease bound to a different actual Pod')
    if sha(os.environ['RISC0_SERVER_PATH']) != '4447bbfa89b450611deda80825387d48cce6d23b428310ac45662f5c65f1cbcb':
        raise ValueError('previously qualified CUDA prover required')
    state_dir.mkdir(mode=0o700, exist_ok=True)
    with (state_dir/'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = state_dir/'ledger.json'
        ledger = json.loads(path.read_text()) if path.exists() else None
        ledger = reserve(ledger, target, expected, lease, time.time())
        output.mkdir(mode=0o700)
        atomic(path, ledger)  # An interrupted stage is consumed; never auto-retry.
        # Reuse the qualified matching-process CUDA sampler and process-group
        # runner. GNU timeout survives loss of this Python/controller process.
        remote = Path(__file__).resolve().parents[2]/'remote-cuda'
        sys.path.insert(0, str(remote))
        from worker import hardware, run_phase
        gpu = hardware()
        atomic(output/'hardware.json', gpu)
        remaining = min(ledger['deadlineUnix'], lease['stopUnix']-300)-time.time()
        args = ['/usr/bin/timeout', '--signal=KILL', f'{remaining:.6f}s', sys.executable,
                str(Path(__file__).resolve()), '--child', str(Path(binary).resolve()),
                str(Path(target_path).resolve()), expected, str(output.resolve())]
        result = run_phase(args, remaining, output/'aggregate', time.monotonic()+remaining, True, gpu['uuid'])
        atomic(output/'phase.json', result)
        if result['exitCode'] != 0 or result['failure'] is not None:
            raise RuntimeError('stage failed; preserve candidate/partial receipts, no retry')
        if time.time() >= ledger['deadlineUnix']:
            raise RuntimeError('aggregate deadline exceeded')
        ledger['completed'].append(target['stage'])
        ledger['lastJournalHex'] = ledger.pop('pendingJournalHex')
        atomic(path, ledger)
        return result


if __name__ == '__main__':
    if len(sys.argv) == 6 and sys.argv[1] == '--child':
        child(sys.argv[2], sys.argv[3], sys.argv[4], Path(sys.argv[5]))
    elif len(sys.argv) == 8:
        print(json.dumps(run(*sys.argv[1:]), indent=2))
    else:
        raise SystemExit('STATE_DIR LEASE_JSON TARGET TARGET_SHA TRUSTED_BINARY BINARY_SHA NEW_OUTPUT')
