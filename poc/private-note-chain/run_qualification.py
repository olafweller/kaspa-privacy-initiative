#!/usr/bin/env python3
"""Fixed local execution-only campaign. No credentials, provider calls or proving."""
import argparse,hashlib,json,os,signal,subprocess,time
from pathlib import Path
CASES=['deposit','credit','transfer','exit','auth-prior-state','auth-covenant','auth-lane','auth-start','zero-native-deposit','wrong-native-script','missing-native-output','zero-deposit-owner','covenant-bound-deposit','duplicate-deposit','wrong-native-destination','old-root-competing-next-batch','cross-batch-replay','credit-then-recovery','recovery-then-credit','malformed-then-valid','invalid-then-valid','valid-invalid-valid']
def group_rss(group):
    total=0
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields=path.read_text().rsplit(') ',1)[1].split()
            if int(fields[2])==group:total+=int(fields[21])*os.sysconf('SC_PAGE_SIZE')
        except (FileNotFoundError,ProcessLookupError,PermissionError):pass
    return total

def main():
    p=argparse.ArgumentParser();p.add_argument('--approved-160m',action='store_true',help='One separately approved valid-invalid-valid run only');p.add_argument('--r0vm',required=True,type=Path);p.add_argument('--host',required=True,type=Path);p.add_argument('--program',required=True,type=Path);p.add_argument('--fixtures',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    runtime_sha=hashlib.sha256(a.r0vm.read_bytes()).hexdigest();assert runtime_sha=='2acdf550f9aca4d05b74072463e4ed307c3824309c754a5cb5f93aa84f3390e6','pinned r0vm mismatch'
    cases=['valid-invalid-valid'] if a.approved_160m else CASES.copy()
    budget=160000000 if a.approved_160m else 128000000
    command_name='profile-160m' if a.approved_160m else 'profile'
    a.out.mkdir();affinity=sorted(os.sched_getaffinity(0))[:4];assert len(affinity)==4
    env=os.environ.copy();env.update(RAYON_NUM_THREADS='4',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',RISC0_PROVER='ipc',RISC0_SERVER_PATH=str(a.r0vm.resolve()));env.pop('RISC0_DEV_MODE',None)
    memory_limit=Path('/sys/fs/cgroup/memory.max');summary={'scope':'EXECUTION_ONLY_NO_RECEIPT_OR_RENTAL','r0vmSha256':runtime_sha,'cycleLimitPerCase':budget,'profile':'APPROVED_SEPARATE_160M_CALIBRATION' if a.approved_160m else 'ORIGINAL_128M','hostSha256':hashlib.sha256(a.host.read_bytes()).hexdigest(),'runnerSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'wallLimitPerCaseSeconds':900,'affinity':affinity,'computeThreads':4,'environmentMemoryLimit':memory_limit.read_text().strip() if memory_limit.exists() else None,'cases':[],'remaining':cases.copy()}
    (a.out/'campaign.json').write_text(json.dumps(summary,indent=2)+'\n')
    for name in cases:
        start=time.monotonic();timedout=False;peak=0
        with (a.out/(name+'.stdout.log')).open('wb') as out,(a.out/(name+'.stderr.log')).open('wb') as err:
            command=['taskset','-c',','.join(map(str,affinity)),str(a.host),command_name,str(a.program),str(a.fixtures),name,str(a.out/name)]
            child=subprocess.Popen(command,env=env,stdout=out,stderr=err,start_new_session=True)
            while True:
                peak=max(peak,group_rss(child.pid));pid,status,usage=os.wait4(child.pid,os.WNOHANG)
                if pid:break
                if time.monotonic()-start>900 and not timedout:os.killpg(child.pid,signal.SIGKILL);timedout=True
                time.sleep(.25)
        code=os.waitstatus_to_exitcode(status);resource={'case':name,'exitCode':code,'timeout':timedout,'wallSeconds':time.monotonic()-start,'peakSampledProcessGroupRssBytes':peak,'wait4MaxRssBytes':usage.ru_maxrss*1024,'userSeconds':usage.ru_utime,'systemSeconds':usage.ru_stime}
        (a.out/(name+'.resources.json')).write_text(json.dumps(resource,indent=2)+'\n')
        summary['cases'].append(resource);summary['remaining'].remove(name);summary['completed']=code==0 and not summary['remaining']
        if code!=0:summary['stoppedAfterFailure']=name
        (a.out/'campaign.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(resource),flush=True)
        if code!=0:return 1
    return 0
if __name__=='__main__':raise SystemExit(main())
