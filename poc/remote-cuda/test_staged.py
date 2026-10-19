"""Real HTTP/subprocess/restart checks, retained proofs, no new proving/GPU/RPC."""
import concurrent.futures
import copy
import io
import gzip
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from common import sha
import staged_package
import staged_policy
import staged_service
import staged_worker
import staged_verify
import staged_archive

TOKEN='synthetic-local-http-token-not-a-credential-0000000000'
ROOT=staged_policy.ROOT


def fixture(package,stage,trial=None):
    base=ROOT/'poc/private-native/evidence'
    old=json.loads((base/'targets.json').read_text())['batches'][stage]
    target={'schema':'KPI_TN10_FROZEN_BATCH_V1','trial':trial or package['trial'],'stage':stage,
        'image':staged_policy.IMAGE,'join':staged_policy.JOIN,'programSha256':staged_policy.PROGRAM,
        'inputSha256':old['inputSha256'],'journalSha256':old['expectedJournalSha256'],
        'journalHex':old['expectedJournalHex'],'stateSha256':sha((base/(stage+'.state.bin')).read_bytes()),
        'cycleLimit':160000000,'aggregateProofSeconds':3600,'segmentPo2':old['segmentPo2'],'automaticRetry':False}
    files={'guest.program.bin':(base/'guest.program.bin').read_bytes(),'input.bin':(base/(stage+'.input.bin')).read_bytes(),
           'journal.bin':(base/(stage+'.journal.bin')).read_bytes(),'target.json':json.dumps(target).encode()}
    return files,sha(files['target.json'])


def archive(files,extra=None):
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w:gz') as tar:
        for name,data in list(files.items())+list(extra or []):
            e=tarfile.TarInfo(name);e.size=len(data);tar.addfile(e,io.BytesIO(data))
    return stream.getvalue()


class HTTP:
    def __init__(self,app):
        self.server=ThreadingHTTPServer(('127.0.0.1',0),staged_service.handler(app))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.port=self.server.server_port
    def close(self):self.server.shutdown();self.server.server_close();self.thread.join()
    def call(self,method,path,value=None,token=TOKEN,headers=None):
        c=HTTPConnection('127.0.0.1',self.port,timeout=10)
        data=value if isinstance(value,bytes) else None if value is None else json.dumps(value).encode()
        h={'Authorization':'Bearer '+token,'Content-Type':'application/json'};h.update(headers or {})
        c.request(method,path,data,h);r=c.getresponse();raw=r.read();code=r.status;c.close()
        return code,raw if path=='/v1/artifacts' else json.loads(raw)


class Staged(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.package=Path(cls.temp.name)/'package'
        cls.policy=staged_package.restore(cls.package)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.volume=Path(self.tmp.name)/'volume'
        self.clock=[time.time()];self.apps=[];self.http=[];self.executions=[]
        self.previous_server=os.environ.get('RISC0_SERVER_PATH');os.environ['RISC0_SERVER_PATH']='/synthetic/no-prover-invoked'
    def tearDown(self):
        for h in self.http:h.close()
        for app in self.apps:app.close()
        if self.previous_server is None:os.environ.pop('RISC0_SERVER_PATH',None)
        else:os.environ['RISC0_SERVER_PATH']=self.previous_server
        self.tmp.cleanup()
    def app(self,mode='normal'):
        def execute(package,assets,digest,out,deadline):
            self.executions.append(assets.name)
            receipt=ROOT/'poc/private-native-proof/gpu-2026-10-18-02/evidence/returned/proofs'/assets.name/'receipt.bin'
            cmd=[sys.executable,str(ROOT/'poc/staged-tn10-service/synthetic_job.py'),str(package/'bin/kpi-private-native-tn10'),str(assets/'target.json'),digest,str(out),str(receipt),mode]
            return staged_worker.execute(package,assets,digest,out,deadline,cuda=False,command=cmd)
        app=staged_service.App(self.package,self.volume,'unittest123',TOKEN,execute=execute,now=lambda:self.clock[0]);self.apps.append(app)
        return app
    def connect(self,app):h=HTTP(app);self.http.append(h);return h
    def configure(self,h):
        now=self.clock[0]
        lease={'podId':'unittest123','createdUnix':now-1,'stopUnix':now+7199,'gpuCount':1,'gpuType':'NVIDIA L40S',
            'actualGpuHourlyUsd':'1.09','actualStorageHourlyUsd':'0.014','stoppedStorageHourlyUsd':'0.0028','retentionHours':24,
            'serviceUrl':'https://unittest123-8080.proxy.runpod.net','workloadScope':staged_policy.SCOPE,'trial':self.policy['trial'],
            'packagePolicySha256':sha((self.package/'staged-policy.json').read_bytes())}
        code,value=h.call('POST','/v1/configure',lease);self.assertEqual(code,200)
        ack={'podId':lease['podId'],'leaseDigest':value['leaseDigest'],'stopUnix':lease['stopUnix']}
        self.assertEqual(h.call('POST','/v1/guard',ack)[0],200)
        return lease,ack
    def submit(self,h,stage,files=None,digest=None):
        files,expected=fixture(self.policy,stage) if files is None else (files,digest)
        data=archive(files)
        return h.call('POST','/v1/stages/'+stage,data,headers={'Content-Type':'application/gzip','X-KPI-Target-Sha256':expected,'X-KPI-Package-Sha256':sha(data)})
    def approve(self,h,stage,digest=None):
        digest=digest or fixture(self.policy,stage)[1]
        return h.call('POST','/v1/targets',{'trial':self.policy['trial'],'stage':stage,'targetSha256':digest})
    def wait(self,h,states):
        end=time.monotonic()+15
        while time.monotonic()<end:
            status=h.call('GET','/v1/status')[1]
            if status['state'] in states:return status
            time.sleep(.02)
        self.fail('local service did not reach expected state')

    def test_four_real_http_arrivals_actual_cpu_verification_and_external_archive(self):
        app=self.app();h=self.connect(app);self.configure(h);deadline=None
        for stage in staged_policy.CASES:
            self.assertEqual(self.approve(h,stage)[0],200)
            code,result=self.submit(h,stage);self.assertEqual(code,202)
            deadline=deadline or result['deadlineUnix'];self.assertEqual(result['deadlineUnix'],deadline)
            status=self.wait(h,('waiting','completed','failed'));self.assertNotEqual(status['state'],'failed')
        self.assertEqual(status['ledger']['completed'],list(staged_policy.CASES))
        self.assertEqual(self.executions,list(staged_policy.CASES))
        code,data=h.call('GET','/v1/artifacts');self.assertEqual(code,200);self.assertEqual(sha(data),status['artifact']['sha256'])
        saved=Path(self.tmp.name)/'returned.tar.gz';saved.write_bytes(data)
        targets={s:{'targetPath':str(app.output/'assets'/s/'target.json'),'targetSha256':fixture(self.policy,s)[1]} for s in staged_policy.CASES}
        index=Path(self.tmp.name)/'trusted-targets.json';index.write_text(json.dumps(targets))
        report=staged_verify.verify(self.package,saved,index,Path(self.tmp.name)/'external-cpu')
        self.assertTrue(report['allFourVerified']);self.assertEqual(report['verifiedCount'],4)

    def test_unauthorized_wrong_target_trial_unknown_or_duplicate_members_rejected(self):
        h=self.connect(self.app());self.configure(h)
        self.assertEqual(h.call('GET','/v1/status',token='wrong')[0],401)
        self.assertEqual(self.submit(h,'deposit')[0],409) # No independent approval.
        self.assertEqual(self.approve(h,'deposit')[0],200)
        files,digest=fixture(self.policy,'deposit')
        self.assertEqual(self.submit(h,'deposit',files,'0'*64)[0],409)
        other,other_digest=fixture(self.policy,'deposit','00'*32)
        self.assertEqual(self.submit(h,'deposit',other,other_digest)[0],409)
        for extra in [[('../escape',b'bad')],[('bin/execute',b'bad')],[('input.bin',b'duplicate')]]:
            data=archive(files,extra)
            self.assertEqual(h.call('POST','/v1/stages/deposit',data,headers={'Content-Type':'application/gzip','X-KPI-Target-Sha256':digest,'X-KPI-Package-Sha256':sha(data)})[0],409)
        self.assertEqual(self.executions,[])

    def test_duplicate_and_concurrent_requests_start_exactly_once(self):
        h=self.connect(self.app());self.configure(h);self.approve(h,'deposit')
        files,digest=fixture(self.policy,'deposit');data=archive(files)
        headers={'Content-Type':'application/gzip','X-KPI-Target-Sha256':digest,'X-KPI-Package-Sha256':sha(data)}
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            replies=list(pool.map(lambda _:h.call('POST','/v1/stages/deposit',data,headers=headers),range(2)))
        self.assertEqual([c for c,_ in replies],[202,202])
        self.assertEqual(sorted(v['alreadyStarted'] for _,v in replies),[False,True])
        self.wait(h,('waiting','failed'));self.assertEqual(self.executions,['deposit'])

    def test_reconnect_waiting_restart_keeps_lease_order_and_deadline(self):
        app=self.app();h=self.connect(app);lease,ack=self.configure(h);self.approve(h,'deposit');self.submit(h,'deposit')
        first=self.wait(h,('waiting','failed'));self.assertEqual(first['state'],'waiting')
        h.close();self.http.remove(h);app.close();self.apps.remove(app)
        app=self.app();h=self.connect(app)
        self.assertFalse(h.call('GET','/v1/status')[1]['guardHeartbeatFresh'])
        self.assertEqual(h.call('POST','/v1/configure',lease|{'stopUnix':lease['stopUnix']-1})[0],409)
        self.assertEqual(h.call('POST','/v1/guard',ack)[0],200)
        self.assertEqual(self.approve(h,'credit-transfer')[0],200)
        reply=self.submit(h,'credit-transfer');self.assertEqual(reply[0],202);self.assertEqual(reply[1]['deadlineUnix'],first['ledger']['deadlineUnix'])
        self.wait(h,('waiting','failed'));self.assertEqual(self.executions,['deposit','credit-transfer'])

    def test_failure_preserves_candidate_and_forbids_later_stage_or_retry(self):
        h=self.connect(self.app(mode='fail'));self.configure(h);self.approve(h,'deposit');self.submit(h,'deposit')
        status=self.wait(h,('failed',));self.assertEqual(status['ledger']['completed'],[])
        self.assertTrue((self.volume/'gpu-attempt/stages/deposit/proof/candidate-receipt.bin').exists())
        self.assertEqual(self.approve(h,'credit-transfer')[0],409)
        self.assertEqual(self.executions,['deposit'])

    def test_original_deadline_expires_between_batches_without_request_reset(self):
        app=self.app();h=self.connect(app);self.configure(h);self.approve(h,'deposit');self.submit(h,'deposit')
        status=self.wait(h,('waiting','failed'));self.assertEqual(status['state'],'waiting')
        self.clock[0]=status['ledger']['deadlineUnix']+1;app.tick()
        self.assertEqual(h.call('GET','/v1/status')[1]['state'],'failed')
        self.assertEqual(self.approve(h,'credit-transfer')[0],409)

    def test_real_external_timeout_kills_stalled_process_group_preserving_candidate(self):
        output=Path(self.tmp.name)/'short-timeout';output.mkdir();assets=Path(self.tmp.name)/'assets';assets.mkdir()
        files,digest=fixture(self.policy,'deposit')
        for n,b in files.items():(assets/n).write_bytes(b)
        receipt=ROOT/'poc/private-native-proof/gpu-2026-10-18-02/evidence/returned/proofs/deposit/receipt.bin'
        command=[sys.executable,str(ROOT/'poc/staged-tn10-service/synthetic_job.py'),str(self.package/'bin/kpi-private-native-tn10'),str(assets/'target.json'),digest,str(output),str(receipt),'stall']
        with self.assertRaises(RuntimeError):staged_worker.execute(self.package,assets,digest,output,time.time()+.5,cuda=False,command=command)
        self.assertTrue((output/'proof/candidate-receipt.bin').exists())
        self.assertNotEqual(json.loads((output/'phase.json').read_text())['exitCode'],0)

    def test_lost_http_response_does_not_cancel_or_repeat_accepted_job(self):
        h=self.connect(self.app());self.configure(h);self.approve(h,'deposit')
        files,digest=fixture(self.policy,'deposit');data=archive(files)
        c=HTTPConnection('127.0.0.1',h.port,timeout=10)
        c.request('POST','/v1/stages/deposit',data,{'Authorization':'Bearer '+TOKEN,'Content-Type':'application/gzip','X-KPI-Target-Sha256':digest,'X-KPI-Package-Sha256':sha(data)})
        c.close()  # Controller disconnects without reading the accepted response.
        status=self.wait(h,('waiting','failed'));self.assertEqual(status['state'],'waiting')
        self.assertEqual(self.executions,['deposit'])

    def test_guard_order_and_single_mutating_process_are_enforced(self):
        app=self.app();h=self.connect(app);self.configure(h)
        with self.assertRaises(BlockingIOError):
            staged_service.App(self.package,self.volume,'unittest123',TOKEN)
        self.assertEqual(self.approve(h,'exit')[0],409)
        self.approve(h,'deposit');app.guard_seen-=31
        self.assertEqual(self.submit(h,'deposit')[0],409);self.assertEqual(self.executions,[])

    def test_changed_asset_or_limits_rejected_before_any_executor(self):
        h=self.connect(self.app());self.configure(h);self.approve(h,'deposit')
        files,digest=fixture(self.policy,'deposit');files['input.bin']=b'changed'
        self.assertEqual(self.submit(h,'deposit',files,digest)[0],409)
        files,digest=fixture(self.policy,'deposit');target=json.loads(files['target.json']);target['aggregateProofSeconds']=7200;files['target.json']=json.dumps(target).encode();digest=sha(files['target.json'])
        self.assertEqual(self.submit(h,'deposit',files,digest)[0],409);self.assertEqual(self.executions,[])

    def test_pax_and_gnu_expansion_rejected_before_tar_parsing_in_both_routes(self):
        files,digest=fixture(self.policy,'deposit')
        baseline=gzip.decompress(archive(files));limit=len(baseline)+1024
        for kind in ('pax','gnu'):
            stream=io.BytesIO()
            with tarfile.open(fileobj=stream,mode='w',format=tarfile.PAX_FORMAT) as tar:
                if kind=='gnu':
                    header=tarfile.TarInfo('././@LongLink');header.type=tarfile.GNUTYPE_LONGNAME
                    metadata=b'x'*(64*1024)+b'\0';header.size=len(metadata)
                    tar.addfile(header,io.BytesIO(metadata))
                for name,data in files.items():
                    member=tarfile.TarInfo(name);member.size=len(data)
                    if kind=='pax':member.pax_headers={'comment':'x'*(64*1024)}
                    tar.addfile(member,io.BytesIO(data))
            data=gzip.compress(stream.getvalue())
            self.assertLess(len(data),staged_policy.MAX_UPLOAD)
            self.assertGreater(len(stream.getvalue()),limit)
            source=Path(self.tmp.name)/(kind+'.tgz');source.write_bytes(data)
            targets=Path(self.tmp.name)/'targets.json';targets.write_text('{}')
            with self.subTest(metadata=kind),patch.object(staged_policy,'MAX_UPLOAD_TAR',limit,create=True),patch.object(staged_verify,'MAX_ARCHIVE_TAR',limit,create=True),patch.object(staged_archive.tarfile,'open',side_effect=AssertionError('tar parser must not run')) as parser:
                with self.assertRaisesRegex(ValueError,'expanded archive limit'):
                    staged_policy.unpack(data,digest,self.policy,'deposit')
                with self.assertRaisesRegex(ValueError,'expanded archive limit'):
                    staged_verify.verify(self.package,source,targets,Path(self.tmp.name)/(kind+'-verify'))
                parser.assert_not_called()

    def test_external_archive_compressed_and_member_limits(self):
        source=Path(self.tmp.name)/'oversize.tgz';source.write_bytes(b'x'*1025)
        targets=Path(self.tmp.name)/'empty-targets.json';targets.write_text('{}')
        with patch.object(staged_verify,'MAX_ARCHIVE',1024,create=True),patch.object(staged_archive.gzip,'GzipFile',side_effect=AssertionError('must reject before gzip')):
            with self.assertRaisesRegex(ValueError,'compressed archive limit'):
                staged_verify.verify(self.package,source,targets,Path(self.tmp.name)/'oversize-verify')
        source.write_bytes(archive({'one':b'','two':b'','three':b''}))
        with patch.object(staged_verify,'MAX_MEMBERS',2,create=True):
            with self.assertRaisesRegex(ValueError,'member limit'):
                staged_verify.verify(self.package,source,targets,Path(self.tmp.name)/'members-verify')
        raw=gzip.decompress(source.read_bytes())
        # The full decompressed size, including tar padding, is allowed at the
        # exact bound; a byte below it must fail before tarfile sees anything.
        with staged_archive.open_archive(source.read_bytes(),source.stat().st_size,len(raw),3) as (_,members):
            self.assertEqual(len(list(members)),3)
        with self.assertRaisesRegex(ValueError,'expanded archive limit'):
            with staged_archive.open_archive(source.read_bytes(),source.stat().st_size,len(raw)-1,3):pass

    def test_second_recovery_reaps_group_after_crash_between_gate_and_kill(self):
        app=self.app();h=self.connect(app);lease,_=self.configure(h)
        files,digest=fixture(self.policy,'deposit');target=json.loads(files['target.json'])
        ledger=staged_policy.reviewed.reserve(None,target,digest,lease,self.clock[0])
        staged_policy.reviewed.atomic(self.volume/'ledger.json',ledger)
        app.state.update(state='running',currentStage='deposit')
        app._save();app.close();self.apps.remove(app)
        output=self.volume/'gpu-attempt/stages/deposit';output.mkdir(parents=True)
        process=subprocess.Popen(['/usr/bin/timeout','--signal=KILL','60s','sleep','60'],start_new_session=True)
        interrupted=staged_service.App.__new__(staged_service.App)
        class SimulatedProcessLoss(BaseException):pass
        try:
            staged_policy.reviewed.atomic(output/'supervision.json',staged_worker.identity(process.pid))
            with patch.object(staged_worker,'stop_interrupted',side_effect=SimulatedProcessLoss):
                with self.assertRaises(SimulatedProcessLoss):
                    interrupted.__init__(self.package,self.volume,'unittest123',TOKEN)
            interrupted.close()
            self.assertEqual(json.loads((self.volume/'state.json').read_text())['state'],'interrupted')
            self.assertIsNone(process.poll(),'first crash must leave the real wait process alive')
            with patch.object(staged_worker,'stop_interrupted',wraps=staged_worker.stop_interrupted) as cleanup:
                recovered=self.app();cleanup.assert_called_once_with(output)
            process.wait(timeout=5);self.assertLess(process.returncode,0)
            self.assertEqual(json.loads((self.volume/'ledger.json').read_text()),ledger)
            self.assertEqual(recovered.state['state'],'interrupted');self.assertEqual(self.executions,[])
            # Repeating cleanup after exit is safe and cannot reset the attempt.
            recovered.close();self.apps.remove(recovered)
            self.assertEqual(self.app().state['state'],'interrupted')
        finally:
            if hasattr(interrupted,'ownership') and not interrupted.ownership.closed:interrupted.close()
            if process.poll() is None:os.killpg(process.pid,9)
            process.wait(timeout=5)

    def test_real_service_process_loss_interrupts_job_and_preserves_deadline(self):
        processes=[]
        def start(mode,index):
            ready=Path(self.tmp.name)/f'ready-{index}.json'
            env=os.environ|{'KPI_SYNTHETIC_TOKEN':TOKEN}
            p=subprocess.Popen([sys.executable,str(ROOT/'poc/staged-tn10-service/synthetic_server.py'),str(self.package),str(self.volume),str(ready),mode],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            processes.append(p);end=time.monotonic()+10
            while time.monotonic()<end:
                if ready.exists():
                    h=HTTP.__new__(HTTP);h.port=json.loads(ready.read_text())['port'];return p,h
                if p.poll() is not None:self.fail('synthetic service failed to start')
                time.sleep(.02)
            self.fail('synthetic service startup timeout')
        try:
            p,h=start('stall',1);self.configure(h);self.approve(h,'deposit');self.submit(h,'deposit')
            registry=self.volume/'gpu-attempt/stages/deposit/supervision.json';end=time.monotonic()+10
            while not registry.exists() and time.monotonic()<end:time.sleep(.02)
            self.assertTrue(registry.exists());deadline=json.loads((self.volume/'ledger.json').read_text())['deadlineUnix']
            p.kill();p.wait(timeout=5)
            _,h=start('normal',2)
            status=h.call('GET','/v1/status')[1]
            self.assertEqual(status['state'],'interrupted');self.assertEqual(status['ledger']['deadlineUnix'],deadline)
            self.assertEqual(status['ledger']['completed'],[])
            self.assertEqual(self.approve(h,'credit-transfer')[0],409)
            code,raw=h.call('GET','/v1/artifacts');self.assertEqual(code,200)
            with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
                self.assertIn('stages/deposit/proof/candidate-receipt.bin',tar.getnames())
        finally:
            for p in processes:
                if p.poll() is None:p.kill()
                p.wait(timeout=5)
            staged_worker.stop_interrupted(self.volume/'gpu-attempt/stages/deposit')

    def test_existing_independent_guard_backs_up_waiting_and_confirms_simulated_stop(self):
        from datetime import datetime,timezone
        from urllib.parse import urlsplit
        from watchdog import Guard
        app=self.app();h=self.connect(app);lease,_=self.configure(h)
        pod={'id':lease['podId'],'createdAt':datetime.fromtimestamp(lease['createdUnix'],timezone.utc).isoformat(),
            'gpuCount':1,'costPerHr':'1.09','gpuTypeId':'NVIDIA L40S','volumeInGb':10,'volumeMountPath':'/workspace',
            'memoryInGb':48,'vcpuCount':4,'desiredStatus':'RUNNING'}
        stops=[]
        def fake_json(url,key,method='GET',value=None):
            if url.startswith('https://rest.runpod.io/'):
                if method=='POST':stops.append(url);pod['desiredStatus']='EXITED'
                return pod.copy()
            code,result=h.call(method,urlsplit(url).path,value);self.assertEqual(code,200);return result
        def fake_bytes(url,key):
            code,result=h.call('GET',urlsplit(url).path);self.assertEqual(code,200);return result
        guard=Guard(lease,Path(self.tmp.name)/'guard','SYNTHETIC-NOT-ACCOUNT-CREDENTIAL',TOKEN,json_call=fake_json,bytes_call=fake_bytes,now=lambda:self.clock[0])
        self.approve(h,'deposit');self.submit(h,'deposit');status=self.wait(h,('waiting','failed'));self.assertEqual(status['state'],'waiting')
        self.assertFalse(guard.step());self.assertEqual(stops,[])
        self.assertTrue((guard.directory/'latest-artifact.json').exists())
        self.clock[0]=status['ledger']['deadlineUnix']+1;app.tick()
        self.assertFalse(guard.step());self.clock[0]+=61
        self.assertTrue(guard.step());self.assertEqual(len(stops),1)
        self.assertTrue(json.loads((guard.directory/'stop.json').read_text())['providerDesiredExitedConfirmed'])


if __name__=='__main__':unittest.main()
