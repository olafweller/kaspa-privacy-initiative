"""Unfunded native TestConsensus input adapter for the actual C gateway.

Only simulation inputs differ. B runs recover_exit(mode='future'), its ordinary
download/Scanner/Full/prover/SDK paths, without native-result memoization.
This archive is separate from public TN10 capture and cannot submit to its node.
Synthetic hashes are never asserted to be real selected-chain block hashes.
"""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import time
import zlib

def require(condition, message):
    if not condition:
        raise ValueError(message)

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def require_rehearsal(cfg):
    require(cfg['mode'] == 'rehearsal' and cfg.get('execution_authorized') is False
            and cfg.get('qualification_only') is True and cfg['run_id'].startswith('qual-a3-'),
            'rehearsal must be separately bound, unfunded and unauthorized for live execution')
    template(cfg)

def template(cfg):
    from capture_metadata import load_capture_metadata
    return load_capture_metadata(cfg['checkpoint_template_path'], 'checkpoint', cfg['checkpoint_template_sha256'])

def checkpoint_metadata(cfg, native):
    require_rehearsal(cfg)
    cp = copy.deepcopy(template(cfg))
    if cfg.get('rehearsal_workload'):
        return cp  # Exact frozen fresh selected-chain checkpoint; native seed is separate.
    # Same live schema/types, with explicitly synthetic native checkpoint identity.
    cursor = native['synthetic_genesis_hash']
    cp.update(seq=0, cursor=cursor, digest='0'*64, blue_score='0', daa_score='0',
              capture_namespace=cfg['capture_namespace'], funding_authorization=False,
              scope='UNFUNDED TestConsensus simulation; real live-schema metadata; no public TN10 acceptance assertion')
    now = time.time()
    native_hash = hashlib.sha256(canonical(native)).hexdigest()
    cp['page_response_sha256'] = native_hash
    for name in ['coverage', 'pre_seal_coverage']:
        if name in cp:
            cp[name]['at'] = now
            cp[name]['namespace'] = cfg['capture_namespace']
            cp[name]['qualified_origin'] = cursor
            for key in ['origin_seal_sha256','baseline_receipt_sha256','initialization_complete_page_sha256','projection_sha256']:
                if key in cp[name]:
                    cp[name][key] = native_hash
            cp[name]['current'].update(seq=0, cursor=cursor, digest='0'*64, at=now, queried_horizon=cursor)
    for name in ['selected_observation', 'pre_seal_observation']:
        if name in cp:
            cp[name].update(at=now, hash=cursor, blue_score='0', daa_score='0')
    for name in ['page_committed_at', 'sealed_at']:
        if name in cp:
            cp[name] = now
    cp['sealed_checkpoint_sha256'] = hashlib.sha256(canonical(cp)).hexdigest()
    return cp

def read(request, cfg, role, call):
    require_rehearsal(cfg)
    action = request['action']
    require(role == 'B', 'rehearsal history belongs to B restricted credential')
    guard = call({'op':'guard', 'run_id':cfg['run_id'], 'authenticated_role':'B'})
    require(guard['recovery_allowed'] and not guard['S1_pointer_supplied'], 'independent loss gate closed')
    run = Path('/var/lib/kpi-capture/boundary-final') / cfg['run_id']
    db = sqlite3.connect('file:' + str(run / 'history.sqlite') + '?mode=ro', uri=True)
    try:
        if action == 'status':
            require(set(request) == {'action'}, 'status request fields')
            metadata = {k:json.loads(v) for k,v in db.execute('select key,value from metadata')}
            return {'metadata':metadata, 'pages':db.execute('select count(*) from pages').fetchone()[0],
                    'bodies':db.execute('select count(*) from bodies').fetchone()[0]}
        if action == 'page':
            require(set(request) == {'action','seq'} and type(request['seq']) is int and 1<=request['seq']<2**63, 'page request')
            row = db.execute('select seq,start,cursor,horizon,response_sha,response,previous_digest,digest,request from pages where seq=?', (request['seq'],)).fetchone()
            require(row is not None, 'rehearsal retained page missing')
            seq,start,cursor,horizon,checksum,blob,previous,digest,raw_request = row
            raw = zlib.decompress(blob)
            require(hashlib.sha256(raw).hexdigest() == checksum, 'rehearsal page checksum')
            return {'seq':seq,'startHash':start,'cursor':cursor,'queried_horizon':horizon,
                    'response_sha256':checksum,'previous_digest':previous,'digest':digest,
                    'request':json.loads(raw_request) if raw_request else {'dataVerbosityLevel':'Full','minConfirmationCount':0},
                    'response':json.loads(raw)}
        if action == 'observations':
            require(set(request) == {'action','after','before'} and all(type(request[k]) is int and request[k]>=0 for k in ['after','before'])
                    and 0<=request['before']-request['after']<=128, 'observation request')
            import fixture_provenance as fp
            accepted = fp.stored(json.loads((run/'accepted-native.json').read_bytes()),json.loads((run/'initial.json').read_bytes()),cfg['fixture_header_adapter_sha256'],cfg['fixture_header_source_patch_sha256'])
            response = {'entries':[{'outpoint':item['transaction']['inputs'][0]['previousOutpoint'], 'utxoEntry':item['input_entry']}
                                   for item in accepted['accepted_path']]}
            last = json.loads(db.execute("select value from metadata where key='last_commit'").fetchone()[0])
            return {'observations':[{'page_seq':last['seq'],'horizon':last['cursor'],
                                    'sha256':hashlib.sha256(canonical(response)).hexdigest(),'response':response}]
                    if request['after']<last['seq']<=request['before'] else []}
        if action == 'utxos':
            require(set(request) == {'action','addresses'} and request['addresses'] == [cfg['S1_address']], 'only rehearsal S1 address permitted')
            import fixture_provenance as fp
            accepted = fp.stored(json.loads((run/'accepted-native.json').read_bytes()),json.loads((run/'initial.json').read_bytes()),cfg['fixture_header_adapter_sha256'],cfg['fixture_header_source_patch_sha256'])
            # The one-shot immutable TestConsensus result is simulation current state.
            # This is not a public-node observation or a fabricated freshness claim.
            return {'server':{'networkId':'testnet-10','isSynced':True,'hasUtxoIndex':True,'serverVersion':'2.1.0'},
                    'utxos':{'entries':[{'outpoint':point,'utxoEntry':entry,'address':cfg['S1_address']}
                                        for point,entry in accepted['current_virtual_utxos']
                                        if entry['scriptPublicKey'] == cfg['S1_spk_hex']]},
                    'scope':'frozen native TestConsensus simulation, never public node',
                    'accepted_native_sha256':hashlib.sha256((run/'accepted-native.json').read_bytes()).hexdigest()}
        raise ValueError('rehearsal read operation forbidden')
    finally:
        db.close()


def initialize_workload_archive(cfg, run):
    """Frozen new-run traffic only; no change to Scanner, native validation or live RPC."""
    require_rehearsal(cfg)
    import shutil
    record = cfg['rehearsal_workload']
    source = Path(record['path'])
    h=hashlib.sha256()
    with source.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    require(h.hexdigest() == record['sha256'], 'workload archive pin mismatch')
    dest = run / 'history.sqlite'
    require(not dest.exists(), 'workload archive already exists')
    shutil.copyfile(source, dest)
    dest.chmod(0o600)
    from recovery_index import Archive
    archive = Archive(dest)
    cp = template(cfg)
    row = archive.db.execute('select cursor,digest from pages where seq=?', (cp['seq'],)).fetchone()
    require(row == (cp['cursor'],cp['digest']), 'fresh workload/checkpoint mismatch')
    last = archive.meta('last_commit')
    require(last['seq']-cp['seq'] == record['pages'], 'frozen workload page count changed')
    require(archive.meta('watch_binding')['run_id'] == cfg['base_instance_id'], 'workload instance binding mismatch')
    return archive
