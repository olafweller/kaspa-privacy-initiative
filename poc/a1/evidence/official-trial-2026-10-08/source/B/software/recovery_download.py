"""Download a complete committed C range without a saved S1 pointer.

This tool only downloads evidence. The pinned Scanner and fresh-terminal/Full
procedure remain mandatory. No submit/broadcast operation exists.
"""

def require(condition, message):
    if not condition:
        raise ValueError(message)
import argparse, hashlib, json, pathlib, time
from history_chunks import Writer
import recovery_errors as errors
from access_check import query

def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':')).encode()

def download(checkpoint, dest, mode='future', run_id=None):
    if mode=='future':
        require(isinstance(run_id,str) and run_id, 'immutable run identity required')
        status_gate=query({'action':'independent','op':'status','run_id':run_id})
        require(status_gate['mode'] in ['live','finite-live-native','rehearsal'] and len(status_gate['events']) in [5,6], 'live loss boundary absent')
        if len(status_gate['events'])==5:
            start=query({'action':'independent','op':'start','run_id':run_id})
        else:
            start={'boundary_digest':status_gate['events'][4]['digest']}
        require(start['boundary_digest']==status_gate['events'][4]['digest'], 'loss boundary changed')
        guard=query({'action':'independent','op':'guard','run_id':run_id});require(guard['recovery_allowed'], 'independent absence gate closed')
        gate={'recovery_allowed':True,'S1_pointer_supplied':False,'run_id':run_id,'boundary_digest':start['boundary_digest']}
    else:
        gate=query({'action':'control-gate','mode':mode})
        require(gate['recovery_allowed'] and not gate['S1_pointer_supplied'], 'shutdown boundary absent')
        start=query({'action':'recovery-start','mode':mode})
        require(start['boundary_digest']==gate['boundary_digest'], 'shutdown boundary changed')
    status = query({'action': 'status'})
    require(status['metadata'].get('last_error') is None, 'capture source unhealthy')
    committed = status['metadata']['last_commit']
    stop = committed['seq']
    require(type(checkpoint['seq']) is int and 0 <= checkpoint['seq'] <= stop, 'checkpoint is outside retained range')
    cursor = checkpoint['cursor']
    previous = checkpoint['digest']
    dest.mkdir(mode=448, exist_ok=False)
    writer = Writer(dest, checkpoint, run_id, committed)
    transfer_start=time.monotonic();validation_seconds=0
    entries = {}
    for seq in range(checkpoint['seq'] + 1, stop + 1):
        if mode=='future': require(query({'action':'independent','op':'guard','run_id':run_id})['recovery_allowed'], 'A reappeared during download')
        row = query({'action': 'page', 'seq': seq})
        require(row['seq'] == seq, 'missing/reordered retained page')
        validation_start=time.monotonic()
        data = canonical(row['response'])
        require(hashlib.sha256(data).hexdigest() == row['response_sha256'], 'corrupt retained response')
        require(row['startHash'] == cursor and row['previous_digest'] == previous, 'page/cursor/hash-chain gap')
        want = hashlib.sha256(canonical({'start': row['startHash'], 'cursor': row['cursor'], 'horizon': row['queried_horizon'], 'response_sha': row['response_sha256'], 'previous_digest': row['previous_digest']})).hexdigest()
        require(row['digest'] == want, 'invalid retained-page digest')
        writer.add(row)
        validation_seconds+=time.monotonic()-validation_start
        if seq%16==0:errors.emit('history-download-progress',{'pages':seq-checkpoint['seq'],'stop_seq':stop})
        cursor = row['cursor']
        previous = row['digest']
    require(cursor == committed['cursor'] and previous == committed['digest'], 'frozen coverage horizon/digest mismatch')
    manifest,manifest_sha256=writer.finish()
    errors.emit('history-download-complete',{'history_pages':manifest['page_count'],'history_semantic_bytes':manifest['semantic_pages_bytes'],'chunks':len(manifest['chunks']),'transfer_and_read_seconds':time.monotonic()-transfer_start,'packaging_validation_seconds':validation_seconds,'manifest_sha256':manifest_sha256})
    from historical_context import Variants
    entries=Variants()
    for begin in range(checkpoint['seq'], stop, 128):
        if mode=='future': require(query({'action':'independent','op':'guard','run_id':run_id})['recovery_allowed'], 'A reappeared during observations')
        observations = query({'action': 'observations', 'after': begin, 'before': min(stop, begin + 128)})['observations']
        for observation in observations:
            response = observation['response']
            require(hashlib.sha256(canonical(response)).hexdigest() == observation['sha256'], 'corrupt UTXO observation')
            for item in response['entries']:
                op = item['outpoint']
                key = op['transactionId'] + ':' + str(op['index'])
                value = item['utxoEntry']
                entries.add(op,value)
    source_record={'horizon':cursor,'checkpoint':checkpoint,'boundary':gate,'node_provenance':status['metadata']['provenance'],'history_manifest_sha256':manifest_sha256,'history_commit':{k:committed[k] for k in ['seq','cursor','digest']}}
    if mode=='future' and status_gate['mode']=='finite-live-native':
        from lifecycle_binding import load_config
        from finite_receipt import historical
        source_record|={'finite_seal':status['finite_seal'],'finite_seal_sha256':status['finite_seal_sha256']}
        historical(load_config(),source_record)
    for name, record in [('entries.json', entries.export()), ('source.json',source_record)]:
        (dest / name).write_bytes(canonical(record))
    return {'pages': manifest['page_count'], 'historical_entries': len(entries), 'horizon': cursor, 'complete_to_frozen_C_commit': True, 'S1_pointer_supplied': False}
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--checkpoint', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    p.add_argument('--run-id', required=True)
    a = p.parse_args()
    print(json.dumps(download(json.loads(a.checkpoint.read_text()), a.output,run_id=a.run_id)))
