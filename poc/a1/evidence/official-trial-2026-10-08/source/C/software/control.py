"""Durable ordered recovery-boundary receipts; contains no broadcaster.

Fixture mode demonstrates ordering only. Live readiness additionally requires
an independently evidenced whole-A isolation hook; a worker stop is not that.
"""

def require(condition, message):
    if not condition:
        raise ValueError(message)
import argparse, fcntl, hashlib, json, os, time
from pathlib import Path
ORDER = ['PREPARED', 'A_VOLATILE_WORKER_READY', 'SUBMITTED_FIXTURE', 'C_ACCEPTED_DURABLE_FIXTURE', 'A_WORKER_UNAVAILABLE_FIXTURE', 'B_RECOVERY_STARTED_FIXTURE', 'COMPLETE_FIXTURE']
LIVE_ORDER = ['PREPARED', 'A_VOLATILE_WORKER_READY', 'A_SUBMISSION_OBSERVED', 'C_ACCEPTED_DURABLE', 'A_UNAVAILABLE', 'B_RECOVERY_STARTED']

def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':')).encode()

def verify(records):
    previous = '0' * 64
    for seq, original in enumerate(records):
        record = dict(original)
        digest = record.pop('digest')
        require(record['seq'] == seq and record['previous'] == previous and (hashlib.sha256(canonical(record)).hexdigest() == digest), 'invalid receipt chain')
        order = ORDER if 'fixture' in record['scope'] else LIVE_ORDER
        require(record['kind'] == order[seq], 'invalid event ordering')
        previous = digest
    return previous

def append(path, kind, payload, mode='fixture'):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_APPEND, 416)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        data = os.read(fd, 1000000)
        lines = data.splitlines()
        previous = '0' * 64
        previous = verify([json.loads(line) for line in lines])
        order = ORDER if mode == 'fixture' else LIVE_ORDER
        require(len(lines) < len(order) and kind == order[len(lines)], 'out-of-order control marker')
        if mode != 'fixture' and kind == 'A_UNAVAILABLE':
            require(payload.get('A_filesystem_unreachable_from_B') is True and payload.get('worker_inactive') is True, 'A loss boundary not demonstrated')
            for key in ['independent_isolation_receipt_sha256', 'volatile_sandbox_receipt_sha256']:
                require(len(payload.get(key, '')) == 64, 'independent isolation receipt required')
        r = {'seq': len(lines), 'kind': kind, 'at': time.time(), 'previous': previous, 'scope': 'unfunded control fixture, not physical-machine failure or live submission' if mode == 'fixture' else 'separately authorized live observation; external isolation trust explicit', 'payload': payload}
        r['digest'] = hashlib.sha256(canonical(r)).hexdigest()
        os.write(fd, canonical(r) + b'\n')
        os.fsync(fd)
        directory = os.open(path.parent, os.O_DIRECTORY)
        os.fsync(directory)
        os.close(directory)
        return r
    finally:
        os.close(fd)

def ready(path):
    records = [json.loads(x) for x in Path(path).read_text().splitlines()]
    return len(records) >= 5 and records[4]['kind'] == 'A_WORKER_UNAVAILABLE_FIXTURE'
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('journal')
    p.add_argument('kind', choices=ORDER)
    p.add_argument('--payload', default='{}')
    a = p.parse_args()
    print(json.dumps(append(a.journal, a.kind, json.loads(a.payload))))
