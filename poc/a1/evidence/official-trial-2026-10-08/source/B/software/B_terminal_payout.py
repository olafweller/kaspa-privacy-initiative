"""Separate G6 phase consumes completed no-broadcast G5; never accesses A/keys."""
import json,pathlib,time
from terminal_wire import capture
from terminal_sdk_gate import encode,sha
from boundary_wait import durable
from access_check import query

def run(config,recovery_directory,result_directory,*,call=query,clock=time.monotonic,sleep=time.sleep):
 root=pathlib.Path(result_directory);result=json.loads((root/'result.json').read_text());receipt=json.loads((root/'C-durable-result-receipt.json').read_text())
 if config['mode']!='finite-live-native' or config.get('execution_authorized') is not True or config.get('terminal_execution_authorized') is not True:raise ValueError('separate concrete terminal authority missing')
 if result['run_id']!=config['run_id'] or result['status']!='success' or result['broadcast'] is not False or result['stage']!='terminal-Full-stop' or result.get('A_dependency') is not False or receipt['result_sha256']!=sha(encode(result)):raise ValueError('durable per-run recovery result missing')
 def C(op,extra=None):return call({'action':'independent','op':op,'run_id':config['run_id']}|(extra or {}))
 # A restart after any terminal intent is reconciliation-only, never submission.
 if (root/'terminal-intent.json').exists():return C('terminal-status')
 C('guard');candidate=capture(config|{'g5_result_sha256':sha(encode(result))},recovery_directory)
 durable(root/'terminal-intent.json',{'run_id':config['run_id'],'candidate_sha256':sha(encode(candidate)),'txid':candidate['decoded']['id'],'full_hash':result['native_Full']['full_hash'],'one_terminal_attempt':True})
 try:submission=C('terminal-submit',{'candidate':candidate})
 except Exception:submission={'outcome':'transport-ambiguous-read-only-reconcile','retry':False}
 durable(root/'terminal-submission-response.json',submission)
 deadline=clock()+2700;initial=None
 while clock()<deadline:
  C('guard')
  status=C('terminal-status')
  if status.get('faulted') or status.get('outcome') in {'rejected-no-retry','expired-or-binding-changed-after-claim-reconcile-only'}:raise ValueError('terminal phase halted')
  phase='initial' if initial is None else 'later'
  observed=C('terminal-observe',{'phase':phase})
  if observed.get('accepted') is True:
   durable(root/('terminal-'+phase+'-receipt.json'),observed)
   if phase=='later':return observed
   initial=observed
  sleep(2)
 raise TimeoutError('terminal acceptance/payout observation deadline; reconcile only')
