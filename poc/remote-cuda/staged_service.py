"""Authenticated four-arrival service; no arbitrary commands or uploaded binaries.

Persistent state and the reviewed reserve() ledger live on one volume. A process
restart interrupts an active job; idle/waiting restarts preserve the same deadline.
The existing independent B guard uses unchanged configure/guard/status/artifacts.
"""
import copy
import fcntl
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import tarfile
import time
from common import lease_check, sha
import staged_policy as policy
import staged_worker
from worker import snapshot

TERMINAL=('completed','failed','interrupted')


class App:
    def __init__(self, package, volume, pod_id, token, execute=staged_worker.execute, now=time.time):
        assert token.isascii() and len(token)>=32 and 'RISC0_DEV_MODE' not in os.environ
        self.package,self.volume,self.pod_id,self.token=package,volume,pod_id,token
        self.policy=policy.check(package)
        self.execute,self.now=execute,now
        self.lock=threading.RLock();self.guard_seen=None
        self.volume.mkdir(parents=True,exist_ok=True)
        self.ownership=(volume/'service.lock').open('a')
        try:fcntl.flock(self.ownership,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BaseException:
            self.ownership.close();raise
        self.output=volume/'gpu-attempt';self.output.mkdir(exist_ok=True)
        self.path=volume/'state.json';self.ledger_path=volume/'ledger.json'
        self.lease=None;self.digest=None
        self.state=json.loads(self.path.read_text()) if self.path.exists() else {
            'state':'unconfigured','phase':'no-lease','scope':policy.SCOPE,
            'trial':self.policy['trial'],'approved':{},'received':{},'results':{}}
        assert self.state['scope']==policy.SCOPE and self.state['trial']==self.policy['trial']
        if (volume/'lease.json').exists():
            self.lease=json.loads((volume/'lease.json').read_text())
            self._validate_lease(self.lease);self.digest=lease_check(self.lease)
        if self.state['state']=='running':
            # Close the launch gate durably BEFORE looking for the group. If
            # its child has not registered yet, it will see interrupted state;
            # if it passed the gate, its group was already registered to kill.
            self.state.update(state='interrupted',phase='service-restarted-no-retry')
            self._save()
        elif self.state['state']!='interrupted' and self.ledger_path.exists():
            ledger=json.loads(self.ledger_path.read_text())
            # Fail closed if a crash split the ledger and service-state writes.
            if ledger['attempted']!=ledger['completed']:
                self.state.update(state='interrupted',phase='incomplete-persistent-stage-no-retry')
                self._save()
        # Repeat cleanup on EVERY interrupted restart, including a crash after
        # the durable gate closure but before the preceding kill. Identity
        # checks make this safe after exit/PID reuse; it never restarts a job.
        if self.state['state']=='interrupted':
            stage=self.state.get('currentStage')
            if stage is not None:
                staged_worker.stop_interrupted(self.output/'stages'/stage)
            self._backup()
        self._save();self.expire()

    def close(self):
        self.ownership.close()

    def _save(self): policy.reviewed.atomic(self.path,self.state)

    def _backup(self):
        public={k:v for k,v in self.state.items() if k!='artifact'}
        policy.reviewed.atomic(self.output/'service-state.json',public)
        if self.lease:policy.reviewed.atomic(self.output/'lease.json',self.lease)
        if self.ledger_path.exists():policy.reviewed.atomic(self.output/'ledger.json',json.loads(self.ledger_path.read_text()))
        self.state['artifact']=snapshot(self.output)
        self._save()

    def _terminal(self,state,reason):
        self.state.update(state=state,phase=reason)
        self._save()
        self._backup()

    def _validate_lease(self,value):
        assert set(value)=={'podId','gpuCount','gpuType','createdUnix','stopUnix','serviceUrl','actualGpuHourlyUsd','actualStorageHourlyUsd','stoppedStorageHourlyUsd','retentionHours','workloadScope','trial','packagePolicySha256'}
        lease_check(value)
        assert value['podId']==self.pod_id and value['createdUnix']<=self.now()+60
        assert value['workloadScope']==policy.SCOPE and value['trial']==self.policy['trial']
        assert value['packagePolicySha256']==sha((self.package/'staged-policy.json').read_bytes())

    def configure(self,value):
        self._validate_lease(value)
        with self.lock:
            if self.lease is not None: assert self.lease==value,'lease cannot change'
            else:
                policy.reviewed.atomic(self.volume/'lease.json',value)
                self.lease=value;self.digest=lease_check(value)
                self.state.update(state='idle',phase='awaiting-first-target')
                self._save()
            self.expire()
            return {'configured':True,'leaseDigest':self.digest}

    def guard(self,value):
        with self.lock:
            assert self.lease is not None and value=={'leaseDigest':self.digest,'podId':self.pod_id,'stopUnix':self.lease['stopUnix']}
            assert self.now()<self.lease['stopUnix']
            self.guard_seen=time.monotonic()
            return {'armed':True,'leaseDigest':self.digest,'stopUnix':self.lease['stopUnix']}

    def fresh_guard(self):
        return self.guard_seen is not None and time.monotonic()-self.guard_seen<30

    def expire(self):
        with self.lock:
            if self.state['state'] in TERMINAL:return
            if self.lease and self.now()>=self.lease['stopUnix']-300:
                self._terminal('failed','effective-lease-transfer-boundary')
            elif self.ledger_path.exists():
                ledger=json.loads(self.ledger_path.read_text())
                if self.now()>=ledger['deadlineUnix']:
                    self._terminal('failed','original-aggregate-deadline-expired')

    def status(self):
        with self.lock:
            self.expire()
            ledger=json.loads(self.ledger_path.read_text()) if self.ledger_path.exists() else None
            return copy.deepcopy(self.state)|{'podId':self.pod_id,'leaseDigest':self.digest,
                'stopUnix':self.lease['stopUnix'] if self.lease else None,
                'packagePolicySha256':sha((self.package/'staged-policy.json').read_bytes()),
                'guardHeartbeatFresh':self.fresh_guard(),'ledger':ledger}

    def approve(self,value):
        with self.lock:
            self.expire()
            assert self.lease is not None and self.state['state'] not in TERMINAL
            assert set(value)=={'trial','stage','targetSha256'} and value['trial']==self.policy['trial']
            stage=value['stage'];assert stage in policy.CASES
            digest=policy.digest(value['targetSha256'])
            old=self.state['approved'].get(stage)
            assert old is None or old==digest,'approved target cannot change'
            index=len(self.state['results'])
            assert index<4 and stage==policy.CASES[index],'only the next stage may be approved'
            self.state['approved'][stage]=digest;self._save()
            return {'approved':True,'stage':stage,'targetSha256':digest}

    def submit(self,stage,target_sha,archive_sha,data):
        policy.digest(target_sha);policy.digest(archive_sha)
        assert sha(data)==archive_sha,'archive transport hash'
        files,target=policy.unpack(data,target_sha,self.policy,stage)
        with self.lock:
            self.expire()
            assert self.lease is not None and self.state['approved'].get(stage)==target_sha,'independently approved target required'
            previous=self.state['received'].get(stage)
            if previous is not None:
                assert previous=={'targetSha256':target_sha,'archiveSha256':archive_sha}
                return {'stage':stage,'alreadyStarted':True,'state':self.state['state']}
            assert self.state['state'] in ('idle','waiting') and self.fresh_guard(),'fresh independent guard and no concurrent job required'
            old=json.loads(self.ledger_path.read_text()) if self.ledger_path.exists() else None
            ledger=policy.reviewed.reserve(copy.deepcopy(old),target,target_sha,self.lease,self.now())
            assets=self.output/'assets'/stage;assets.mkdir(parents=True)
            for name in policy.PUBLIC:policy.write(assets/name,files[name])
            output=self.output/'stages'/stage;output.mkdir(parents=True)
            self.state['received'][stage]={'targetSha256':target_sha,'archiveSha256':archive_sha}
            self.state.update(state='running',phase=stage,currentStage=stage)
            # Both records are durable before launching anything. A split write
            # on restart cannot reset/redo the consumed attempt.
            self._save();policy.reviewed.atomic(self.ledger_path,ledger)
            self._backup()
            deadline=min(ledger['deadlineUnix'],self.lease['stopUnix']-300)
            threading.Thread(target=self._run,args=(stage,assets,target_sha,output,deadline),daemon=True).start()
            return {'stage':stage,'alreadyStarted':False,'deadlineUnix':ledger['deadlineUnix']}

    def _run(self,stage,assets,target_sha,output,deadline):
        try:
            result=self.execute(self.package,assets,target_sha,output,deadline)
            with self.lock:
                self.expire()
                if self.state['state']!='running':
                    self._backup();return
                ledger=json.loads(self.ledger_path.read_text())
                assert self.now()<deadline and ledger['attempted'][-1]==stage
                ledger['completed'].append(stage)
                ledger['lastJournalHex']=ledger.pop('pendingJournalHex')
                policy.reviewed.atomic(self.ledger_path,ledger)
                self.state['results'][stage]=result
                self.state.update(state='completed' if len(ledger['completed'])==4 else 'waiting',phase='awaiting-chain-checkpoint' if len(ledger['completed'])<4 else 'four-stages-completed-in-container')
                self._backup()
        except Exception as error:
            with self.lock:
                # Public diagnostics only. Never serialize tokens/environments.
                self.state['failureType']=type(error).__name__
                self._terminal('failed','stage-failed-no-retry')

    def tick(self):
        with self.lock:
            self.expire()
            if self.state['state']=='running':self._backup()


def handler(app):
    class Handler(BaseHTTPRequestHandler):
        protocol_version='HTTP/1.1'
        def setup(self):super().setup();self.connection.settimeout(10)
        def log_message(self,*args):pass
        def authorized(self):
            value=self.headers.get('Authorization','')
            return value.isascii() and hmac.compare_digest(value,'Bearer '+app.token)
        def reply(self,code,value):
            data=json.dumps(value).encode();self.send_response(code)
            self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers()
            try:self.wfile.write(data)
            except (BrokenPipeError,ConnectionResetError):pass
        def do_GET(self):
            self.close_connection=True
            if not self.authorized():return self.reply(401,{'error':'unauthorized'})
            if self.path=='/v1/status':return self.reply(200,app.status())
            if self.path=='/v1/artifacts':
                with app.lock:
                    archive=app.output/'artifacts.tar.gz'
                    if not archive.exists():return self.reply(409,{'error':'no checkpoint archive'})
                    data=archive.read_bytes()
                self.send_response(200);self.send_header('Content-Type','application/gzip');self.send_header('Content-Length',str(len(data)));self.end_headers()
                try:self.wfile.write(data)
                except (BrokenPipeError,ConnectionResetError):pass
                return
            self.reply(404,{'error':'unknown fixed route'})
        def do_POST(self):
            self.close_connection=True
            if not self.authorized():return self.reply(401,{'error':'unauthorized'})
            try:
                assert self.headers.get('Transfer-Encoding') is None
                length=int(self.headers.get('Content-Length','0'));assert 0<length<=policy.MAX_UPLOAD
                data=self.rfile.read(length);assert len(data)==length
                prefix='/v1/stages/'
                if self.path.startswith(prefix):
                    stage=self.path[len(prefix):];assert stage in policy.CASES
                    assert self.headers.get('Content-Type')=='application/gzip'
                    value=app.submit(stage,self.headers.get('X-KPI-Target-Sha256'),self.headers.get('X-KPI-Package-Sha256'),data)
                    return self.reply(202,value)
                assert length<=4096
                value=json.loads(data)
                if self.path=='/v1/configure':return self.reply(200,app.configure(value))
                if self.path=='/v1/guard':return self.reply(200,app.guard(value))
                if self.path=='/v1/targets':return self.reply(200,app.approve(value))
                self.reply(404,{'error':'unknown fixed route'})
            except (AssertionError,ValueError,KeyError,TypeError,OSError,EOFError,tarfile.TarError):
                self.reply(409,{'error':'invalid public package, target, lease or attempt state'})
    return Handler


def serve(app,server):
    def monitor():
        while True:
            try:app.tick()
            except OSError:pass  # Absolute B stop is independent of backup I/O.
            time.sleep(2)
    threading.Thread(target=monitor,daemon=True).start();server.serve_forever()


if __name__=='__main__':
    # bind/volume mounts may share st_dev with their parent under Docker VFS.
    # Require an actual mount-table entry instead of os.path.ismount().
    assert any(line.split()[4]=='/workspace' for line in Path('/proc/self/mountinfo').read_text().splitlines()),'persistent /workspace mount required'
    policy.check(Path('/opt/kpi/staged-tn10'),cuda=True)
    app=App(Path('/opt/kpi/staged-tn10'),Path('/workspace/kpi-staged-tn10'),os.environ['RUNPOD_POD_ID'],os.environ['KPI_GPU_TOKEN'])
    serve(app,ThreadingHTTPServer(('0.0.0.0',8080),handler(app)))
