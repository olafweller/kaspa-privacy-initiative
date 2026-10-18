"""Credential-free package, orchestration and REAL watchdog tests; no proving."""
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from common import sha
import lifecycle_package as pkg
import lifecycle_runner as runner
import lifecycle_worker as lifecycle
from lifecycle_control import verify
from service import App
from test_remote import lease, TOKEN
import worker


def dead(pid):
    p=Path(f'/proc/{pid}/stat')
    return not p.exists() or p.read_text().rsplit(')',1)[1].split()[0]=='Z'


class Lifecycle(unittest.TestCase):
    def package(self,root):
        p=root/'package';pkg.restore(p);return p

    def test_fixed_package_and_all_compiled_targets_without_execution(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.package(Path(d));pkg.check(p)
            for case in pkg.CASES:
                r=subprocess.run([str(p/'bin'/pkg.BINS[0]),'check-target',case,str(p/'inputs')],capture_output=True,text=True,timeout=30)
                self.assertEqual(r.returncode,0,r.stderr)
            for name in pkg.INPUTS:
                f=p/'inputs'/name;raw=f.read_bytes();f.write_bytes(raw+b'x')
                with self.assertRaises(AssertionError):pkg.check(p)
                f.write_bytes(raw)
            policy=json.loads((p/'lifecycle-workload.json').read_text());changed=copy.deepcopy(policy)
            changed['aggregateProofProcessGroupSecondsLimit']=4*3600
            (p/'lifecycle-workload.json').write_text(json.dumps(changed))
            with self.assertRaises(AssertionError):pkg.check(p)

    def test_journal_continuity_cannot_be_replaced(self):
        for offset,label in [(64,'state root discontinuity'),(96,'lane tip discontinuity')]:
            with tempfile.TemporaryDirectory() as d:
                p=self.package(Path(d));f=p/'inputs/deposit.journal.bin'
                data=bytearray(f.read_bytes());data[offset]^=1;f.write_bytes(data)
                tfile=p/'inputs/targets.json';target=json.loads(tfile.read_text())
                target['batches']['deposit']['expectedJournalHex']=data.hex()
                target['batches']['deposit']['expectedJournalSha256']=sha(data)
                tfile.write_text(json.dumps(target))
                with self.assertRaisesRegex(AssertionError,label):pkg.continuity(p/'inputs')

    def test_partial_results_survive_later_stage_failure_and_verification_is_trusted(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=self.package(root);out=root/'out';out.mkdir()
            def synthetic(case,kind,args):
                if case=='credit-transfer' and kind=='prove':return 17
                if kind=='prove':
                    f=out/'proofs'/case;f.mkdir(parents=True);(f/'receipt.bin').write_bytes(b'synthetic-orchestration-only')
                return 0
            with self.assertRaises(RuntimeError):runner.run(p,out,executor=synthetic)
            self.assertTrue((out/'proofs/deposit/receipt.bin').exists())
            self.assertFalse((out/'pipeline-complete.json').exists())
            import shutil
            shutil.copytree(p/'inputs',out/'assets')
            commands=[]
            result=verify(p,out,root/'verified',executor=lambda a:commands.append(a))
            self.assertEqual(result['verifiedCount'],1)
            self.assertFalse(result['allFourCryptographicallyVerified'])
            self.assertEqual(Path(commands[0][0]),(p/'bin'/pkg.BINS[1]).resolve())
            self.assertNotIn(str(out/'bin'),commands[0][0])

    def test_stage_list_has_one_proof_and_independent_check_per_case_and_native_exit(self):
        stages=list(runner.stages(Path('/trusted'),Path('/results')))
        self.assertEqual([(c,k) for c,k,_ in stages],[(c,k) for c in pkg.CASES for k in (('prove','cpu-verify','native-exit') if c=='exit' else ('prove','cpu-verify'))])

    def test_real_children_obey_nonrecursive_rust_output_directory_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=self.package(root);out=root/'output';out.mkdir()
            standin=root/'filesystem_contract_only.py'
            standin.write_text('import sys;from pathlib import Path;'
                'target=Path(sys.argv[-1]);target.mkdir();'
                '\nif sys.argv[1]=="prove":(target/"receipt.bin").write_bytes(b"SYNTHETIC-NOT-A-PROOF")\n')
            real_popen=subprocess.Popen
            commands=[]
            def child(arguments,**kwargs):
                commands.append(arguments)
                # Real subprocesses enforce the pinned Rust create_dir contract;
                # no crypto/prover command or package executable is invoked.
                return real_popen([sys.executable,str(standin),*arguments[1:]],**kwargs)
            with patch.object(runner.subprocess,'Popen',side_effect=child):
                records=runner.run(p,out)
            self.assertEqual(len(records),9)
            self.assertTrue(all(x['exitCode']==0 for x in records))
            self.assertEqual(len(commands),9)
            for case in pkg.CASES:
                self.assertTrue((out/'proofs'/case/'receipt.bin').is_file())
                self.assertTrue((out/'cpu'/case).is_dir())
            self.assertTrue((out/'native-exit').is_dir())

    def test_single_start_and_missing_guard_remain_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            app=App(Path('/unused'),Path(d),'unittest123',TOKEN,execute=lifecycle.execute,scope=pkg.SCOPE)
            app.configure(lease())
            self.assertEqual(app.status()['scope'],pkg.SCOPE)
            with self.assertRaises(AssertionError):app.start()
            with patch('lifecycle_worker.hardware') as gpu,patch('lifecycle_worker.run_phase') as run:
                with self.assertRaises(AssertionError):lifecycle.execute(Path('/unused'),Path('/unused'),{'stopUnix':0},lambda v:None)
                run.assert_not_called();gpu.assert_not_called()

    def test_real_aggregate_deadline_keeps_first_artifact_and_kills_later_descendant(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);pid=root/'child.pid';first=root/'completed-receipt.bin'
            code=('import os,subprocess,time;from pathlib import Path;'
                  'assert "KPI_GPU_TOKEN" not in os.environ and "RUNPOD_API_KEY" not in os.environ;'
                  f'Path({str(first)!r}).write_bytes(b"synthetic-stage-one");'
                  'p=subprocess.Popen(["sleep","60"]);'
                  f'Path({str(pid)!r}).write_text(str(p.pid));time.sleep(60)')
            with patch.dict(os.environ,{'RISC0_SERVER_PATH':sys.executable,'KPI_GPU_TOKEN':TOKEN,'RUNPOD_API_KEY':'test-only'}),patch.object(worker,'CPU_COUNT',min(4,len(os.sched_getaffinity(0)))):
                report=worker.run_phase(['/usr/bin/timeout','--signal=KILL','0.8s',sys.executable,'-c',code],3600,root/'aggregate',time.monotonic()+.8,False,'')
            self.assertNotEqual(report['exitCode'],0)
            self.assertEqual(report['failure'],'aggregate-or-lease-deadline')
            self.assertEqual(first.read_bytes(),b'synthetic-stage-one')
            self.assertTrue(dead(int(pid.read_text())))

    def test_external_watchdog_survives_controlling_process_death(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);pid=root/'descendant';guard=root/'watchdog'
            child='import subprocess,time;from pathlib import Path;p=subprocess.Popen(["sleep","60"]);'+f'Path({str(pid)!r}).write_text(str(p.pid));time.sleep(60)'
            control='import subprocess,time;from pathlib import Path;p=subprocess.Popen('+repr(['/usr/bin/timeout','--signal=KILL','1.5s',sys.executable,'-c',child])+',start_new_session=True);'+f'Path({str(guard)!r}).write_text(str(p.pid));time.sleep(60)'
            controller=subprocess.Popen([sys.executable,'-c',control],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                end=time.monotonic()+3
                while not pid.exists() and time.monotonic()<end:time.sleep(.02)
                self.assertTrue(pid.exists());controller.kill();controller.wait(timeout=2)
                end=time.monotonic()+4
                while not dead(int(pid.read_text())) and time.monotonic()<end:time.sleep(.05)
                self.assertTrue(dead(int(pid.read_text())), 'orphaned prover escaped external timer')
            finally:
                if controller.poll() is None:controller.kill();controller.wait()
                if guard.exists():
                    try:os.killpg(int(guard.read_text()),signal.SIGKILL)
                    except ProcessLookupError:pass


if __name__=='__main__':unittest.main()
