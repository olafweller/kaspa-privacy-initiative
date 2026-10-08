"""Independent B loss guard around unchanged native recovery. No broadcaster."""
import sys,os,subprocess,time,json,pathlib,signal,argparse
from access_check import query
from durable_result import atomic
import recovery_errors as errors
p=argparse.ArgumentParser()
p.add_argument('--mode',choices=['future'],required=True)
p.add_argument('--run-id',required=True)
for n in ['public','backup','locator','checkpoint','output']:p.add_argument('--'+n,type=pathlib.Path,required=True)
p.add_argument('--inventory-sha256',required=True)
a=p.parse_args();started=time.monotonic();checks=0
errors.initialize(os.environ['KPI_RECOVERY_DIAGNOSTIC_DIR']);errors.register_backup(a.backup);errors.stage('independent-absence-guard')

def C(op):return query({'action':'independent','op':op,'run_id':a.run_id})
def supervised():
 s=C('status')
 if s['mode'] not in ['live','finite-live-native','rehearsal'] or len(s['events']) not in [5,6]:raise ValueError('live independently observed A-loss boundary absent')
 if len(s['events'])==5:C('start')
 
 def guard():
  global checks
  g=C('guard')
  if not g['recovery_allowed'] or g['S1_pointer_supplied']:raise ValueError('independent absence guard closed')
  checks+=1
 
 guard();child=subprocess.Popen(['/usr/bin/python3','/software/recover_exit.py',*sys.argv[1:]],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);streams=errors.attach_child(child)
 try:
  while child.poll() is None:
   if time.monotonic()-started>=5400:raise ValueError('90-minute recovery budget exceeded')
   guard();time.sleep(2)
  errors.collect_child(child,streams);streams=None
  if child.returncode:raise ValueError('native recovery rejected')
  guard();r=json.loads((a.output/'report.json').read_text())
  if not (r['discovery']['state']=='s1' and r['fresh_terminal_proof'] and r['separate_native_Full'] and r['SDK_roundtrip_decoded_native_Full'] and r['broadcast'] is False and r['A_access_required'] is False):raise ValueError('G5 recovery outcome incomplete')
  atomic(a.output/'independent-absence-receipt.json',{'run_id':a.run_id,'loss_digest':s['events'][4]['digest'],'guard_checks':checks,'elapsed_seconds':time.monotonic()-started,'fresh_terminal_and_Full':True,'broadcast':False})
  print('Independent guarded S1 recovery and fresh terminal Full validation complete; STOP before broadcast.')
 except BaseException:
  if child.poll() is None:os.killpg(child.pid,signal.SIGKILL)
  child.wait()
  if streams is not None:errors.collect_child(child,streams)
  raise

errors.guarded(supervised)
