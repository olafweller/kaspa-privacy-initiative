"""Isolated finite-prefix sampled-node witness. No submit/broadcast API.

A trusted C-local config pins a read-only validator-created seal. This module
checks bindings and current node assertions; it does not validate that historical
prefix or turn node assertions into a cryptographic light-client proof.
"""
from __future__ import annotations
import base64, hashlib, json, math, os, pathlib, re, socket, stat, struct, time

class Reject(ValueError): pass

def require(ok, why):
    if not ok: raise Reject(why)

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def digest(value): return hashlib.sha256(canonical(value)).hexdigest()
def hexhash(value): return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None

def integer(value, low=0, high=2**64-1):
    return type(value) is int and low <= value <= high

def finite(value): return type(value) in (int, float) and math.isfinite(value)

def strict_json(raw):
    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result, 'duplicate JSON key'); result[k] = v
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(Reject('nonfinite JSON')))

def survival(response, endpoint):
    require(type(response) is dict and set(response) == {
        'removedChainBlockHashes', 'addedChainBlockHashes', 'acceptedTransactionIds'}, 'V1 response fields')
    removed, added, accepted = (response[k] for k in (
        'removedChainBlockHashes', 'addedChainBlockHashes', 'acceptedTransactionIds'))
    require(type(removed) is list and type(added) is list and type(accepted) is list, 'V1 array types')
    # Any removal faults. Do not parse/reconcile an unbounded removed vector.
    require(not removed, 'sealed endpoint removed')
    require(not accepted, 'unexpected accepted transaction IDs')
    require(len(added) <= 2480 and all(hexhash(h) for h in added), 'added hash budget/format')
    require(len(set(added)) == len(added) and endpoint not in added, 'duplicate/endpoint addition')
    return {'endpoint_survives_sample': True, 'tip_reached': False,
            'added_count': len(added), 'response_sha256': digest(response)}

def process_identity():
    # PID alone permits reuse; Linux process start tick and boot ID are also bound.
    start = pathlib.Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]
    return {'boot': pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'pid': os.getpid(), 'start_ticks': int(start)}

def durable_new(path, value):
    raw = canonical(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)
    except BaseException:
        # Partial evidence remains; this instance cannot be resumed.
        raise

class Store:
    """One observer lifetime only. Existing directory is never resumed.

    seal_path, expected digest and owner UID are trusted C-local config. They must
    never be accepted from B requests. Historical native validation is external.
    """
    def __init__(self, directory, seal_path, expected_seal_sha256, expected_owner_uid,
                 *, wall=time.time, mono=time.monotonic, identity=process_identity,
                 max_samples=10000, lifetime=12500, max_bytes=10000*1024*1024):
        self.wall, self.mono, self.identity = wall, mono, identity
        self.owner = expected_owner_uid
        require(integer(expected_owner_uid) and expected_owner_uid == os.getuid(), 'C owner UID')
        require(integer(max_samples, 1, 10000) and integer(lifetime, 1, 12500), 'observer budget')
        require(integer(max_bytes, 1024, 10000*1024*1024), "archive byte budget")
        self.max_samples, self.lifetime = max_samples, lifetime
        self.max_bytes, self.bytes = max_bytes, 0
        self.seal_path = pathlib.Path(seal_path)
        fd = os.open(self.seal_path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            s = os.fstat(fd)
            require(s.st_uid == self.owner and stat.S_ISREG(s.st_mode) and stat.S_IMODE(s.st_mode) == 0o600
                    and s.st_nlink == 1 and s.st_size <= 2*1024*1024, 'untrusted seal ownership/mode/size')
            with os.fdopen(fd, 'rb', closefd=False) as f: raw = f.read(2*1024*1024+1)
        finally: os.close(fd)
        require(hexhash(expected_seal_sha256) and hashlib.sha256(raw).hexdigest() == expected_seal_sha256, 'C config seal pin')
        self.seal_raw, self.seal_sha = raw, expected_seal_sha256
        self._seal = strict_json(raw)
        self._validate_seal()
        self.directory = pathlib.Path(directory)
        for parent in (self.seal_path.parent,self.directory.parent):
            st=parent.stat(); require(st.st_uid==self.owner and stat.S_ISDIR(st.st_mode) and not st.st_mode&0o022, 'untrusted C parent directory')
        self.directory.mkdir(mode=0o700)  # EEXIST means crashed/restarted/reused run: reject.
        require(stat.S_IMODE(self.directory.stat().st_mode) == 0o700, 'private observer directory')
        self.observer = identity(); self.started = mono(); self.started_wall = wall()
        self.seq = 0; self.previous = digest({'seal_sha256': self.seal_sha, 'observer': self.observer})
        self.failed = False; self.last = None
        durable_new(self.directory/'START.json', {'schema':'kpi-seal-observer-start/v1',
            'seal_sha256':self.seal_sha, 'observer':self.observer, 'at':self.started_wall,
            'run_id':self.seal['run_id'], 'lifetime':lifetime, 'max_samples':max_samples})

    @property
    def seal(self):
        return strict_json(self.seal_raw)  # Defensive copy; never trust a caller-mutated dict.

    def _validate_seal(self):
        s = self.seal
        require(type(s) is dict and set(s) == {'schema','run_id','network','genesis','endpoint','active_chain',
            'continuation','config_sha256','role_sources_sha256','native_sha256','sdk_sha256',
            'checkpoint_sha256','prefix_sha256','history_manifest_sha256','server_version','phase'}, 'seal fields')
        require(isinstance(s['server_version'],str) and 1<=len(s['server_version'])<=160, 'server version pin')
        require(s['schema'] == 'kpi-C-native-validated-prefix-seal/v1' and s['network'] == 'testnet-10', 'seal scope')
        require(isinstance(s['run_id'],str) and re.fullmatch('[a-zA-Z0-9_-]{1,100}',s['run_id']), 'seal run')
        require(all(hexhash(s[k]) for k in ['genesis','endpoint','config_sha256','role_sources_sha256',
            'native_sha256','sdk_sha256','checkpoint_sha256','prefix_sha256','history_manifest_sha256']), 'seal pins')
        chain = s['active_chain']
        require(type(chain) is list and 1 <= len(chain) <= 20000 and all(hexhash(h) for h in chain)
                and len(chain) == len(set(chain)) and chain[-1] == s['endpoint'], 'seal projection')
        c = s['continuation']
        require(s['phase'] in ('pre-funding','s1'), 'seal phase')
        if s['phase']=='pre-funding': require(c is None, 'prefunding continuation forbidden')
        else:
            require(type(c) is dict and set(c) == {'txid','full_hash','accepting_hash'}
                and all(hexhash(v) for v in c.values()) and c['accepting_hash'] in chain, 'seal body mapping')

    def fault(self, why, timing=None):
        self.failed = True
        if not (self.directory/'FAULT.json').exists():
            durable_new(self.directory/'FAULT.json', {'schema':'kpi-seal-observer-fault/v1',
                'run_id':self.seal['run_id'], 'seal_sha256':self.seal_sha, 'observer':self.observer,
                'seq':self.seq, 'at':self.wall(), 'reason':str(why)[:200],
                'timing':timing})

    def check(self, sampling=False):
        try: self._check(sampling)
        except BaseException as e:
            self.fault(type(e).__name__+': '+str(e)); raise

    def _check(self, sampling=False):
        require(not self.failed and not (self.directory/'FAULT.json').exists(), 'faulted observer')
        require(self.identity() == self.observer, 'observer identity changed')
        require(0 <= self.mono()-self.started <= self.lifetime, 'observer lifetime')
        require(not sampling or self.seq < self.max_samples, 'observer sample budget')
        # Reopen the trusted file without following replacements; pin original bytes each gate.
        fd = os.open(self.seal_path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            s=os.fstat(fd)
            require(s.st_uid == self.owner and stat.S_IMODE(s.st_mode)==0o600 and s.st_nlink==1
                    and stat.S_ISREG(s.st_mode) and s.st_size==len(self.seal_raw), 'seal changed permissions')
            with os.fdopen(fd,'rb',closefd=False) as f: raw=f.read(len(self.seal_raw)+1)
        finally: os.close(fd)
        require(raw == self.seal_raw, 'seal bytes changed')

    def commit(self, observations, began_wall, began_mono, ended_wall, ended_mono):
        try: return self._commit(observations,began_wall,began_mono,ended_wall,ended_mono)
        except BaseException as e:
            self.fault(type(e).__name__+': '+str(e), self.timing('commit',began_wall,began_mono,ended_wall,ended_mono)); raise

    def timing(self, stage, bw=None, bm=None, ew=None, em=None):
        # Source-constant stage + numeric timing only; never request/body/keys.
        ew=self.wall() if ew is None else ew;em=self.mono() if em is None else em
        wd=ew-bw if finite(ew) and finite(bw) else None
        md=em-bm if finite(em) and finite(bm) else None
        return {'stage':stage,'sample_guard_seconds':8,'receipt_start_max_age_seconds':15,
                'wall_duration_seconds':wd,'monotonic_duration_seconds':md,
                'clock_disagreement_seconds':abs(wd-md) if wd is not None and md is not None else None}

    def _commit(self, observations, began_wall, began_mono, ended_wall, ended_mono):
        self.check(sampling=True)
        require(all(finite(x) for x in (began_wall,began_mono,ended_wall,ended_mono)), 'sample timing values')
        require(0 <= ended_mono-began_mono <= 8 and 0 <= ended_wall-began_wall <= 8, 'sample duration deadline')
        require(abs((ended_wall-began_wall)-(ended_mono-began_mono)) <= 1, 'sample clock disagreement')
        require(0 <= self.mono()-began_mono <= 8 and -2 <= self.wall()-began_wall <= 8, 'stale sample start')
        payload={'schema':'kpi-C-prefix-current-sample/v1','run_id':self.seal['run_id'],
            'seal_sha256':self.seal_sha,'observer':self.observer,'seq':self.seq+1,'previous_digest':self.previous,
            'started_at':began_wall,'completed_at':ended_wall,'started_monotonic':began_mono,'completed_monotonic':ended_mono,'duration':ended_mono-began_mono,
            'observations':observations, 'trust':'sampled validating C node assertion; non-atomic RPC bracket'}
        receipt=payload|{'digest':digest(payload)}
        encoded=canonical(receipt); require(len(encoded)<=1024*1024 and self.bytes+len(encoded)<=self.max_bytes, 'receipt/archive byte budget')
        durable_new(self.directory/f'{self.seq+1:06d}.json', receipt)
        self.seq += 1; self.bytes+=len(encoded); self.previous=receipt['digest']; self.last=(strict_json(encoded),began_mono,began_wall)
        return strict_json(encoded)

    def latest(self, max_age=15):
        try:
            self.check(); require(self.last is not None, 'no current receipt')
            receipt, started_mono, started_wall=self.last
            require(finite(max_age) and 0 < max_age <= 15 and 0 <= self.mono()-started_mono <= max_age
                    and -2 <= self.wall()-started_wall <= max_age, 'stale receipt start')
            p=self.directory/f'{self.seq:06d}.json'; require(strict_json(p.read_bytes())==receipt, 'receipt bytes changed')
            return strict_json(canonical(receipt))
        except BaseException as e:
            self.fault(type(e).__name__+': '+str(e)); raise

class BoundedRPC:
    """Read-only websocket JSON RPC. Explicit deadline and cap before payload read.

    Connect is injected by the C-local adapter; this class never chooses an endpoint.
    No general user-controlled method forwarding or submission methods exist.
    """
    METHODS={'getServerInfo','getBlock','getBlockDagInfo','getVirtualChainFromBlock','getUtxosByAddresses'}
    def __init__(self, connect, *, mono=time.monotonic, deadline=8, wire_cap=512*1024):
        require(integer(deadline,1,8) and integer(wire_cap,1024,512*1024),'transport budget')
        self.mono=mono; self.deadline=mono()+deadline; self.wire_cap=wire_cap
        self.n=0; self.buf=bytearray(); self.s=connect(deadline)
        try: self._handshake()
        except BaseException:
            self.s.close(); raise

    def _handshake(self):
        self.s.settimeout(self.remaining())
        key=base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(('GET / HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: '+key+'\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        while b'\r\n\r\n' not in self.buf:
            require(len(self.buf)<8192,'handshake budget'); self.s.settimeout(self.remaining())
            part=self.s.recv(min(4096,8192-len(self.buf))); require(part,'handshake EOF'); self.buf.extend(part)
        header, rest=bytes(self.buf).split(b'\r\n\r\n',1); self.buf=bytearray(rest)
        expected=base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest())
        lines=header.split(b'\r\n'); require(lines[0] in (b'HTTP/1.1 101 Switching Protocols',b'HTTP/1.1 101'),'handshake status')
        headers={}
        for line in lines[1:]:
            k,v=line.split(b':',1); k=k.strip().lower(); require(k not in headers,'duplicate handshake header'); headers[k]=v.strip().lower() if k in (b'upgrade',b'connection') else v.strip()
        require(headers.get(b'sec-websocket-accept')==expected and headers.get(b'upgrade')==b'websocket'
                and b'upgrade' in headers.get(b'connection',b'').split(b', '),'handshake identity')

    def remaining(self):
        left=self.deadline-self.mono(); require(left>0,'RPC deadline'); return left
    def read(self,n):
        require(n<=self.wire_cap,'wire allocation budget')
        while len(self.buf)<n:
            self.s.settimeout(self.remaining()); part=self.s.recv(min(65536,n-len(self.buf)))
            require(part,'RPC EOF'); self.buf.extend(part)
        self.remaining(); result=bytes(self.buf[:n]); del self.buf[:n]; return result
    def send(self,payload,op=1):
        self.s.settimeout(self.remaining()); n=len(payload); require(n<=8192,'request budget')
        mask=os.urandom(4); h=bytes([128|op,128|(n if n<126 else 126)])
        if n>=126: h+=struct.pack('!H',n)
        self.s.sendall(h+mask+bytes(b^mask[i%4] for i,b in enumerate(payload)))
    def receive(self):
        data=bytearray(); fragmented=False; controls=0; frames=0
        while True:
            frames+=1; require(frames<=128,'frame count budget')
            a,b=self.read(2); require(a&0x70==0 and b&128==0,'unsupported/masked server frame')
            n=b&127
            if n==126: n=struct.unpack('!H',self.read(2))[0]; require(n>=126,'noncanonical frame length')
            elif n==127: n=struct.unpack('!Q',self.read(8))[0]; require(n>=65536 and n<2**63,'noncanonical frame length')
            op=a&15
            if op in (8,9,10):
                require(a&128 and n<=125,'control frame shape'); controls+=1; require(controls<=8,'control frame budget')
                require(n+len(data)<=self.wire_cap,'wire message budget'); p=self.read(n)
                if op==8: raise Reject('RPC closed')
                if op==9: self.send(p,10)
                continue
            require(op==(0 if fragmented else 1),'unexpected fragment/opcode')
            require(n+len(data)<=self.wire_cap,'wire message budget')
            data.extend(self.read(n))
            if a&128: return strict_json(data)
            fragmented=True
    def call(self,method,params):
        require(method in self.METHODS,'read-only RPC allowlist')
        self.n+=1; self.send(canonical({'id':self.n,'method':method,'params':params})); result=self.receive()
        require(type(result) is dict and type(result.get('id')) is int and result['id']==self.n
                and result.get('method')==method and set(result)=={'id','method','params'},'RPC identity/error/fields')
        self.remaining(); return result['params']
    def close(self): self.s.close()

class Sampler:
    def __init__(self, store, rpc_factory, addresses, genesis_verifier=None):
        self.store,self.rpc_factory=store,rpc_factory
        self.genesis_verifier=genesis_verifier
        require(type(addresses) is list and 1<=len(addresses)<=8 and len(set(addresses))==len(addresses)
                and all(isinstance(a,str) and a.startswith('kaspatest:') and len(a)<=150 for a in addresses),'address budget')
        # Trusted C config must own this exact predeclared set; B cannot extend it.
        self.addresses=tuple(addresses)
    def qualified(self,info):
        require(type(info) is dict and info.get('networkId')=='testnet-10' and info.get('isSynced') is True
                and info.get('hasUtxoIndex') is True
                and info.get('serverVersion')==self.store.seal['server_version'],'node health/version')
    def sample(self):
        s=self.store; rpc=None;bw=bm=None;stage='sample-start'
        try:
            s.check(sampling=True); bw,bm=s.wall(),s.mono(); rpc=self.rpc_factory()
            stage='server-before';before=rpc.call('getServerInfo',{}); self.qualified(before)
            if self.genesis_verifier is None:
                genesis=rpc.call('getBlock',{'hash':s.seal['genesis'],'includeTransactions':False})
                require(genesis.get('block',{}).get('header',{}).get('hash')==s.seal['genesis'],'genesis mismatch/unavailable')
            else:
                stage='node-identity-before';genesis=self.genesis_verifier(); require(genesis['genesis']==s.seal['genesis'] and genesis['network']=='testnet-10','pinned node genesis mismatch')
            request={'startHash':s.seal['endpoint'],'includeAcceptedTransactionIds':False,'minConfirmationCount':0}
            stage='survival-before';first=rpc.call('getVirtualChainFromBlock',request); survival(first,s.seal['endpoint'])
            stage='utxo-bracket';utxos=rpc.call('getUtxosByAddresses',{'addresses':list(self.addresses)})
            self.check_utxos(utxos)
            stage='survival-after';second=rpc.call('getVirtualChainFromBlock',request); survival(second,s.seal['endpoint'])
            stage='dag-context';dag=rpc.call('getBlockDagInfo',{}); require(type(dag) is dict and integer(dag.get('virtualDaaScore')) and integer(dag.get('pastMedianTime')) and hexhash(dag.get('sink')), 'native DAG context')
            stage='server-after';after=rpc.call('getServerInfo',{}); self.qualified(after)
            stage='node-identity-after'
            if self.genesis_verifier is not None: require(self.genesis_verifier()==genesis, 'node identity changed across sample')
            ew,em=s.wall(),s.mono(); rpc.close(); rpc=None
            return s.commit({'server_before':before,'genesis':genesis,'request':request,'survival_before':first,
                'addresses':list(self.addresses),'utxos':utxos,'survival_after':second,'dag':dag,'server_after':after},bw,bm,ew,em)
        except BaseException as e:
            s.fault(type(e).__name__+': '+str(e),s.timing(stage,bw,bm)); raise
        finally:
            if rpc is not None: rpc.close()
    def check_utxos(self,response):
        require(type(response) is dict and set(response)=={'entries'} and type(response['entries']) is list
                and len(response['entries'])<=8,'UTXO budget/fields')
        seen=set()
        for item in response['entries']:
            require(type(item) is dict and set(item)=={'address','outpoint','utxoEntry'}
                    and item['address'] in self.addresses,'UTXO address/fields')
            op,entry=item['outpoint'],item['utxoEntry']
            require(type(op) is dict and set(op)=={'transactionId','index'} and hexhash(op['transactionId'])
                    and integer(op['index'],0,2**32-1),'UTXO outpoint')
            key=(op['transactionId'],op['index']); require(key not in seen,'duplicate UTXO'); seen.add(key)
            require(type(entry) is dict and set(entry)=={'amount','scriptPublicKey','blockDaaScore','isCoinbase','covenantId'}
                    and integer(entry['amount']) and integer(entry['blockDaaScore']) and type(entry['isCoinbase']) is bool
                    and (entry['covenantId'] is None or hexhash(entry['covenantId'])),'native UTXO entry')
            # Pinned ScriptPublicKey::serialize emits version.to_be_bytes() + script as
            # one human-readable hex string, not its accepted deserialization dict form.
            spk=entry['scriptPublicKey']; require(isinstance(spk,str) and 4<=len(spk)<=20004
                and re.fullmatch('(?:[0-9a-f]{2})+',spk) is not None,'native UTXO script wire encoding')
