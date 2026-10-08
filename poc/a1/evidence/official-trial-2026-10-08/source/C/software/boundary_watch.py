"""Read-only accepted-lineage boundary checker, no funding/broadcast API.

Call on C in the separately authorized future run. It checks an exact archived
range and independently retained historical entries with pinned native Full.
Its receipt belongs on C; A should receive only an opaque release signal.
"""

def require(condition, message):
    if not condition:
        raise ValueError(message)
import hashlib, json, sqlite3, zlib
from pathlib import Path
import a1_recovery as r

def validate_boundary(database, manifest, locator, checkpoint, inventory_hash, entries, binary, reference):
    db = sqlite3.connect('file:' + str(database) + '?mode=ro', uri=True)
    last = db.execute("SELECT value FROM metadata WHERE key='last_commit'").fetchone()
    last = json.loads(last[0])
    require(last is not None and type(checkpoint['seq']) is int and 0 <= checkpoint['seq'] <= last['seq'], 'checkpoint outside committed archive')
    horizon = last['cursor']
    expected_seq = checkpoint['seq'] + 1
    scanner = r.Scanner(locator, manifest, r.native_callback(binary, reference, entries), inventory_hash)
    previous = checkpoint['digest']
    cursor = checkpoint['cursor']
    for seq, start, end, query_horizon, check, blob, prev, digest in db.execute('SELECT seq,start,cursor,horizon,response_sha,response,previous_digest,digest FROM pages WHERE seq>? AND seq<=? ORDER BY seq', (checkpoint['seq'], last['seq'])):
        require(seq == expected_seq, 'missing/reordered archive page')
        expected_seq += 1
        data = zlib.decompress(blob)
        wanted = hashlib.sha256(json.dumps({'start': start, 'cursor': end, 'horizon': query_horizon, 'response_sha': check, 'previous_digest': prev}, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        require(digest == wanted, 'invalid archive page digest')
        require(start == cursor and prev == previous and (hashlib.sha256(data).hexdigest() == check), 'archive boundary gap/checksum failure')
        scanner.page({'startHash': start, 'response': json.loads(data)}, horizon)
        cursor = end
        previous = digest
    require(expected_seq == last['seq'] + 1 and cursor == horizon and previous == last['digest'], 'incomplete archive boundary')
    report = scanner.report(horizon)
    require(report['lineage_history_complete'] and report['state'] == 's1' and (len(report['transitions']) == 1), 'exact accepted continuation is not durably established')
    return {'schema': 'kpi-g5-accepted-boundary/v1', 'accepted_continuation_native_Full': True, 'range_complete': True, 'C_commit_digest': last['digest'], 'C_commit_seq': last['seq'], 'S0_locator_sha256': hashlib.sha256(json.dumps(locator, sort_keys=True, separators=(',', ':')).encode()).hexdigest(), 'state_discovered': 's1', 'acceptance_trust': 'validated C node observation, not cryptographic light-client proof'}
