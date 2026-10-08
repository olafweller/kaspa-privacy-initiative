"""Forced SSH command: bounded retained pages/status and read-only UTXO RPC."""

def require(condition, message):
    if not condition:
        raise ValueError(message)
import argparse, hashlib, json, os, re, sqlite3, stat, sys, zlib
from pathlib import Path
from rpc_local import RPC
ROOT = Path('/var/lib/kpi-capture')
CONTROL_SOCKET='/run/kpi-g5-independent/control.sock'
CONTROLLER_UID=None

def trusted_route(argv):
    # Arguments are frozen in the root-owned forced SSH command, never parsed
    # from SSH_ORIGINAL_COMMAND or from the bounded client request.
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--role',choices=['B','controller'],default='B')
    for name in ['config','config-sha256','bound-run','control-socket']:parser.add_argument('--'+name)
    args=parser.parse_args(argv);values=[args.config,args.config_sha256,args.bound_run,args.control_socket]
    require(not any(values) or all(values),'complete trusted route arguments required')
    if not any(values):return args.role,None,CONTROL_SOCKET
    require(re.fullmatch('[a-z0-9][a-z0-9-]{7,119}',args.bound_run) is not None and re.fullmatch('[0-9a-f]{64}',args.config_sha256) is not None,'trusted route run/hash format')
    path=Path(args.config);socket_path=Path(args.control_socket)
    require(path.is_absolute() and socket_path.is_absolute() and '..' not in path.parts and '..' not in socket_path.parts and str(socket_path).endswith('/control.sock'),'absolute trusted config/socket paths')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        metadata=os.fstat(stream.fileno())
        require(stat.S_ISREG(metadata.st_mode) and metadata.st_uid==0 and metadata.st_nlink==1 and not stat.S_IMODE(metadata.st_mode)&0o022 and metadata.st_size<=262144,'trusted root-owned immutable config file')
        raw=stream.read(262145)
    require(len(raw)<=262144 and hashlib.sha256(raw).hexdigest()==args.config_sha256,'trusted config bytes changed')
    def pairs(rows):
        value={}
        for key,item in rows:require(key not in value,'duplicate trusted config field');value[key]=item
        return value
    config=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite trusted config')))
    require(config.get('mode')=='finite-live-native' and config.get('run_id')==args.bound_run,'trusted finite run mismatch')
    # Socket peer identity is authenticated by the private root-owned containing
    # directory and Unix permissions, plus controller SO_PEERCRED role checks.
    controller_uid=config.get('controller_uid',0);require(type(controller_uid) is int and 0<=controller_uid<2**32,'trusted controller UID')
    parent=socket_path.parent
    require(not parent.is_symlink() and parent.is_dir(),'trusted socket directory')
    st=parent.stat();require(st.st_uid==0 and not stat.S_IMODE(st.st_mode)&0o022,'trusted root-owned socket directory')
    st=socket_path.lstat();require(stat.S_ISSOCK(st.st_mode) and st.st_uid==controller_uid,'trusted controller socket owner/type')
    return args.role,config,str(socket_path)


def independent_call(request, limit=262144):
    import socket
    sock=socket.socket(socket.AF_UNIX);sock.settimeout(1800);sock.connect(CONTROL_SOCKET)
    if CONTROLLER_UID is not None:
        import struct
        _,peer_uid,_=struct.unpack('3i',sock.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12));require(peer_uid==CONTROLLER_UID,'trusted controller peer UID')
    sock.sendall(json.dumps(request,separators=(',',':')).encode()+b'\n')
    with sock.makefile('rb') as stream:response=stream.readline(limit+1)
    sock.close();require(len(response)<=limit and response.endswith(b'\n'),'independent response oversized/incomplete');result=json.loads(response)
    if 'error' in result:raise ValueError(result['error'])
    return result

def live_read_gate(role, action, config, call=independent_call):
    if config['mode']!='live':return
    require(action not in {'boundary-v2','fixture','control-gate','recovery-start','acceptance-gate'}, 'legacy gate cannot authorize a live run')
    if role=='B' and action in {'page','observations','utxos'}:
        require(config.get('execution_authorized') is True,'live execution not authorized')
        guard=call({'run_id':config['run_id'],'op':'guard','authenticated_role':'B'})
        require(guard.get('recovery_allowed') is True and guard.get('S1_pointer_supplied') is False,'live history reads before independent loss forbidden')

def finite_request(request,role,config,call=independent_call):
 require(config['mode']=='finite-live-native','finite gateway mode');require(type(request) is dict and not set(request)&{'config','config_sha256','control_socket','authenticated_role','role'},'client routing fields forbidden');action=request.get('action')
 if 'run_id' in request:require(request['run_id']==config['run_id'],'finite client run mismatch')
 if action=='checkpoint':
  require(role=='controller' and set(request)=={'action'},'finite checkpoint role/fields')
  return call({'run_id':config['run_id'],'op':'finite-checkpoint','authenticated_role':role})
 if action in ['status','page','observations','utxos']:
  if role=='controller':
   require(action=='status' and set(request)=={'action'},'controller opaque finite status only')
   return call({'run_id':config['run_id'],'op':'status','authenticated_role':role})
  return call({'run_id':config['run_id'],'op':'finite-read','request':request,'authenticated_role':'B'},limit=65*1024**2)
 if action=='independent':
  allowed={'intent','sandbox','status','funding-ready'} if role=='controller' else {'arm','start','guard','status','result','lineage-hint','terminal-submit','terminal-observe','terminal-status'}
  require(request.get('op') in allowed and 'authenticated_role' not in request,'finite credential operation forbidden')
  return call({k:v for k,v in request.items() if k!='action'}|{'authenticated_role':role})
 raise ValueError('legacy gateway action forbidden in finite mode')

def main():
    global CONTROL_SOCKET,CONTROLLER_UID
    role,config,CONTROL_SOCKET=trusted_route(sys.argv[1:]);CONTROLLER_UID=None if config is None else config.get('controller_uid',0)
    data = sys.stdin.buffer.readline(16385)
    if len(data) > 16384 or not data.endswith(b'\n'):
        raise ValueError('bounded JSON request required')
    r = json.loads(data)
    action = r.get('action')
    if role == 'controller' and action not in {'status', 'checkpoint', 'acceptance-gate', 'boundary-v2', 'independent'}:
        raise ValueError('controller is restricted to opaque acceptance/status receipts')
    if config is None:config=json.loads(Path('/etc/kpi-g5-independent.json').read_text())
    if config['mode']=='finite-live-native':
        print(json.dumps(finite_request(r,role,config),separators=(',',':')))
        return
    live_read_gate(role,action,config)
    if config['mode']=='rehearsal' and action in {'status','page','observations','utxos'}:
        require(role=='B','rehearsal history belongs to B credential')
        result=independent_call({'op':'rehearsal-read','request':r,'run_id':config['run_id'],'authenticated_role':'B'},limit=64*1024**2)
        print(json.dumps(result,separators=(',',':')))
        return
    if config['mode']=='live' and role=='B' and action in {'status','page','observations'}:
        result=independent_call({'op':'bounded-log-read','request':r,'run_id':config['run_id'],'authenticated_role':'B'},limit=64*1024**2)
        print(json.dumps(result,separators=(',',':')))
        return
    db = sqlite3.connect('file:' + str(ROOT / 'history.sqlite') + '?mode=ro', uri=True, timeout=15)
    if action == 'independent':
        import socket
        allowed={'intent','fixture-submit','sandbox','status'} if role=='controller' else {'arm','start','guard','fixture-data','status','result','lineage-hint'}
        require(r.get('op') in allowed and 'authenticated_role' not in r,'independent operation forbidden for credential')
        request={k:v for k,v in r.items() if k!='action'}|{'authenticated_role':role}
        sock=socket.socket(socket.AF_UNIX);sock.settimeout(1800);sock.connect('/run/kpi-g5-independent/control.sock');sock.sendall(json.dumps(request,separators=(',',':')).encode()+b'\n')
        with sock.makefile('rb') as stream:response=stream.readline(262145)
        sock.close();require(len(response)<=262144 and response.endswith(b'\n'),'independent response oversized/incomplete');result=json.loads(response)
        if 'error' in result:raise ValueError(result['error'])
    elif action == 'boundary-v2':
        import socket
        allowed_ops = {'submit','observe','sandbox','arm','loss','status'} if role == 'controller' else {'start','fixture-data','status'}
        require(r.get('op') in allowed_ops and 'authenticated_role' not in r, 'boundary operation forbidden for credential')
        request = {k:v for k,v in r.items() if k!='action'} | {'authenticated_role': role}
        sock = socket.socket(socket.AF_UNIX);sock.settimeout(1800);sock.connect('/run/kpi-g5-boundary/control.sock');sock.sendall(json.dumps(request,separators=(',',':')).encode()+b'\n')
        with sock.makefile('rb') as stream:
            response = stream.readline(262145)
        sock.close();require(len(response)<=262144 and response.endswith(b'\n'), 'boundary response oversized/incomplete');result=json.loads(response)
        if 'error' in result:raise ValueError(result['error'])
    elif action == 'status' and set(r) == {'action'}:
        meta = {k: json.loads(v) for k, v in db.execute('SELECT key,value FROM metadata')}
        result = {'metadata': meta, 'pages': db.execute('SELECT COUNT(*) FROM pages').fetchone()[0], 'bodies': db.execute('SELECT COUNT(*) FROM bodies').fetchone()[0]}
    elif action == 'checkpoint' and set(r) == {'action'}:
        from checkpoint_horizon import checkpoint
        result=checkpoint(db,json.loads(Path('/etc/kpi-capture.json').read_text()),json.loads(Path('/etc/kpi-g5-independent.json').read_text()),RPC)
    elif action == 'page' and set(r) == {'action', 'seq'} and (type(r['seq']) is int) and (1 <= r['seq'] < 2 ** 63):
        row = db.execute('SELECT seq,start,cursor,horizon,response_sha,response,previous_digest,digest,request FROM pages WHERE seq=?', (r['seq'],)).fetchone()
        if not row:
            raise ValueError('required retained page missing')
        seq, start, cursor, horizon, check, blob, previous, digest, request = row
        data = zlib.decompress(blob)
        if hashlib.sha256(data).hexdigest() != check:
            raise ValueError('retained page checksum mismatch')
        result = {'seq': seq, 'startHash': start, 'cursor': cursor, 'queried_horizon': horizon, 'response_sha256': check, 'previous_digest': previous, 'digest': digest, 'request': json.loads(request) if request else {'legacy_request_reconstruction': 'from source: Full/minConfirmationCount=0'}, 'response': json.loads(data)}
    elif action == 'observations' and set(r) == {'action', 'after', 'before'} and all((type(r[k]) is int and r[k] >= 0 for k in ['after', 'before'])) and (r['before'] - r['after'] <= 128):
        rows = db.execute('SELECT page_seq,horizon,response_sha,response FROM utxo_observations WHERE page_seq>? AND page_seq<=? ORDER BY seq', (r['after'], r['before'])).fetchall()
        result = {'observations': [{'page_seq': seq, 'horizon': h, 'sha256': check, 'response': json.loads(zlib.decompress(blob))} for seq, h, check, blob in rows]}
    elif action == 'acceptance-gate' and set(r) == {'action'}:
        from control import verify
        p = Path('/var/lib/kpi-g5-control/future-run.jsonl')
        if not p.exists():
            raise ValueError('live accepted boundary not armed')
        records = [json.loads(x) for x in p.read_text().splitlines()]
        verify(records)
        found = [x for x in records if x['kind'] == 'C_ACCEPTED_DURABLE']
        if not found:
            raise ValueError('no independently captured accepted continuation')
        payload = found[-1]['payload']
        if not payload.get('accepted_continuation_native_Full') or not payload.get('range_complete'):
            raise ValueError('accepted boundary did not pass native/coverage checks')
        result = {'accepted_continuation_native_Full': True, 'range_complete': True, 'boundary_digest': found[-1]['digest'], 'S1_pointer_supplied': False}
    elif action in {'control-gate', 'recovery-start'} and set(r) == {'action', 'mode'} and (r['mode'] in {'fixture', 'future'}):
        require(r['mode']=='fixture', 'legacy live gate disabled; run-bound boundary-v2 receipt required')
        name = 'preparation-fixture.jsonl'
        p = Path('/var/lib/kpi-g5-control') / name
        if not p.exists():
            raise ValueError('required independent shutdown boundary absent')
        records = [json.loads(x) for x in p.read_text().splitlines()]
        from control import verify
        verify(records)
        expected = 'A_WORKER_UNAVAILABLE_FIXTURE' if r['mode'] == 'fixture' else 'A_UNAVAILABLE'
        found = [x for x in records if x['kind'] == expected]
        if not found:
            raise ValueError('original environment has not crossed shutdown boundary')
        result = {'recovery_allowed': True, 'scope': r['mode'], 'boundary_digest': found[-1]['digest'], 'S1_pointer_supplied': False}
        if action == 'recovery-start':
            import time, uuid
            receipt = result | {'event': 'B_RECOVERY_STARTED', 'at': time.time(), 'authentication': 'dedicated B-only restricted SSH credential'}
            output = Path('/var/lib/kpi-history/recovery-starts') / (uuid.uuid4().hex + '.json')
            data = json.dumps(receipt, sort_keys=True, separators=(',', ':')).encode()
            fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 384)
            try:
                os.write(fd, data)
                os.fsync(fd)
            finally:
                os.close(fd)
            d = os.open(output.parent, os.O_DIRECTORY)
            os.fsync(d)
            os.close(d)
            result['C_recovery_start_receipt_sha256'] = hashlib.sha256(data).hexdigest()
    elif action == 'fixture' and set(r) == {'action', 'name'} and (r['name'] in {'locator.json', 'pages.json', 'entries.json', 'current-utxos.json', 'current-entries.json', 'source.json', 'pre-funding-checkpoint.json'}):
        data = (Path('/opt/kpi-g5-capture/fixtures/abrupt-s1') / r['name']).read_bytes()
        result = {'scope': 'previously-published-unfunded-native-fixture-not-live-TN10', 'name': r['name'], 'sha256': hashlib.sha256(data).hexdigest(), 'data': json.loads(data)}
    elif action == 'utxos' and set(r) == {'action', 'addresses'}:
        addresses = r['addresses']
        if not isinstance(addresses, list) or len(addresses) > 8 or any((not isinstance(a, str) or not a.startswith('kaspatest:') or len(a) > 150 for a in addresses)):
            raise ValueError('invalid bounded TN10 addresses')
        allowed = json.loads(Path('/etc/kpi-capture.json').read_text()).get('watch_addresses', [])
        if not addresses or not set(addresses).issubset(allowed):
            raise ValueError('only predeclared low-cardinality reserve addresses allowed')
        # B never triggers the node's unbounded address-result API. Read a
        # recent independently captured native UTXO observation instead.
        import time
        row = db.execute('SELECT at,horizon,addresses_sha,response_sha,response FROM utxo_observations ORDER BY seq DESC LIMIT 1').fetchone()
        require(row is not None, 'current retained UTXO observation missing')
        observed_at, horizon, addresses_sha, response_sha, blob = row
        require(addresses_sha == hashlib.sha256(json.dumps(allowed, sort_keys=True, separators=(',', ':')).encode()).hexdigest(), 'watch configuration not yet observed')
        require(-2 <= time.time() - observed_at <= 15, 'current UTXO observation stale')
        raw = zlib.decompress(blob)
        require(len(raw) <= 16 * 1024 * 1024 and hashlib.sha256(raw).hexdigest() == response_sha, 'retained UTXO observation corrupt/oversized')
        observed = json.loads(raw)
        require(len(observed['entries']) <= 8, 'reserve cardinality exceeds bounded experiment budget')
        require(json.loads(db.execute("SELECT value FROM metadata WHERE key='last_error'").fetchone()[0]) is None, 'capture unhealthy')
        # Entries retain their native address; an unexpected/non-address entry
        # must never be silently interpreted as the requested reserve.
        filtered = [entry for entry in observed['entries'] if entry.get('address') in addresses]
        rpc = RPC()
        try:
            info = rpc.call('getServerInfo', {})
            require(info['networkId'] == 'testnet-10' and info['isSynced'] and info['hasUtxoIndex'], 'node not qualified')
            dag = rpc.call('getBlockDagInfo', {})
            result = {'server': info, 'dag_at_read': dag, 'utxos': {'entries': filtered},
                      'observation_at': observed_at, 'observation_age_seconds': time.time()-observed_at,
                      'observation_horizon': horizon, 'retained_response_sha256': response_sha,
                      'scope': 'fresh retained C native UTXO snapshot; not B-triggered address enumeration'}
        finally:
            rpc.close()
    else:
        raise ValueError('gateway action forbidden')
    print(json.dumps(result, separators=(',', ':')))
if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(json.dumps({'error': type(e).__name__ + ': ' + str(e)}))
        sys.exit(1)
