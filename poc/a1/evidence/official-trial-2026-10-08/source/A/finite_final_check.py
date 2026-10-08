"""Source-bound native final handoff gates adapted from qualified Q checks.
C-private accepted S1 values remain on C; output contains only existing digests.
Read-only code does not create another finite observer or change lifecycle state.
"""
import json,hashlib,time
from launcher_common import E,read,sha,remote,durable

def check(cfg,b):
 C='INSTALLED='+repr(b['C'])+'\nCFG='+repr(cfg)+'\n'+r'''
import pathlib,json,sys,hashlib,sqlite3,time,subprocess
root=pathlib.Path(INSTALLED['source_root'])
for n,h in INSTALLED['source_pins'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
raw=pathlib.Path(INSTALLED['config_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==INSTALLED['config_sha256'] and json.loads(raw)==CFG
sys.path.insert(0,str(root));from finite_runtime import settings,node_binding,database,config_digest;from rpc_local import RPC;from a1_recovery import rpc_spk,rpc_uint;from seal_witness import survival,digest;import boundary_controller_v2 as boundary
settings(CFG);node_binding(CFG);run=pathlib.Path(CFG['finite']['root'])/CFG['run_id'];rows=boundary.events(run);boundary.verify_chain(rows);assert [x['kind'] for x in rows]==['PREPARED','C_ACCEPTED_DURABLE','A_NO_DURABLE_S1_VERIFIED','A_LOSS_ARMED'];assert not (run/'FAULT.json').exists() and not (run/'B-result.json').exists()
v=json.loads((run/'validation-result.json').read_bytes())['receipt'];assert v['range_complete'] and v['accepted_continuation_native_Full'] and v['state_discovered']=='s1';assert rows[1]['payload']['matched_intended_txid_and_full_hash'];assert (run/'validation-completed.json').exists()
intent=json.loads((run/'intent.json').read_bytes());seal=json.loads((run/'S1-SEAL.json').read_bytes());assert seal['config_sha256']==config_digest(CFG) and seal['role_sources_sha256']==digest(CFG['finite']['role_sources']) and seal['continuation']['txid']==intent['intended_txid'] and seal['continuation']['full_hash']==intent['full_hash']
db=sqlite3.connect('file:'+str(database(CFG))+'?mode=ro',uri=True,timeout=3)
spends=db.execute('SELECT DISTINCT a.txid,a.full_hash FROM spends s JOIN acceptance a USING(full_hash) JOIN recovery_index_chain c ON c.hash=a.accepting_hash AND c.page_seq=a.page_seq WHERE s.previous_txid=? AND s.previous_index=?',(CFG['locator']['s0_txid_hex'],0)).fetchall();assert spends==[(intent['intended_txid'],intent['full_hash'])];db.close()
started=time.time();r=RPC();r.METHODS=set(r.METHODS)|{'getVirtualChainFromBlock'}
try:
 info=r.call('getServerInfo',{});assert info['networkId']=='testnet-10' and info['serverVersion']==CFG['finite']['server_version'] and info['isSynced'] and info['hasUtxoIndex'];req={'startHash':seal['endpoint'],'includeAcceptedTransactionIds':False,'minConfirmationCount':0};survival(r.call('getVirtualChainFromBlock',req),seal['endpoint']);utxos=r.call('getUtxosByAddresses',{'addresses':CFG['finite']['watch_addresses']})['entries'];survival(r.call('getVirtualChainFromBlock',req),seal['endpoint'])
finally:r.close()
assert -2<=time.time()-started<=15 and len(utxos)<=8;node_binding(CFG)
m=json.loads(pathlib.Path(CFG['manifest']).read_bytes());matches=[x for x in utxos if x['outpoint']=={'transactionId':intent['intended_txid'],'index':0}];assert len(matches)==1;u=matches[0]['utxoEntry'];assert rpc_uint(u['amount'])==rpc_uint(m['states']['s1']['R']) and rpc_spk(u['scriptPublicKey']).hex()==m['states']['s1']['spk_hex'] and u['covenantId'] is None and u['isCoinbase'] is False;assert not any(x['outpoint']=={'transactionId':CFG['locator']['s0_txid_hex'],'index':0} for x in utxos)
from lease_state import read_state
lease=read_state();assert lease['state']=='reachable' and lease['certain'];sandbox=json.loads((run/'sandbox.json').read_bytes());assert all(sandbox[k] for k in ['all_persistent_mounts_read_only','work_is_tmpfs','swap_max_zero','stdout_stderr_null','core_disabled','actual_persistent_write_attempt_EROFS'])
opaque={'schema':'kpi-g5-opaque-C-acceptance/v1'}
# Read exact stored C receipt from its role-bound process rather than duplicate observer state.
import socket
with socket.socket(socket.AF_UNIX) as s:
 s.settimeout(15);s.connect(INSTALLED['socket_root']+'/control.sock');s.sendall(json.dumps({'run_id':CFG['run_id'],'op':'status','authenticated_role':'controller'}).encode()+b'\n');status=json.loads(s.makefile('rb').readline(262145))
assert status['latest_probe']['all_reachable'] and not status['latest_probe']['uncertain'] and -2<=time.time()-status['latest_probe']['at']<=5 and not status['faulted'];assert status['receipt']['acceptance_digest']==rows[1]['digest']
print(json.dumps({'passed':True,'run_id':CFG['run_id'],'at':time.time(),'C_complete_native_Full':True,'C_current_exact_S1_unspent':True,'C_unique_active_S0_spend':True,'A_online_certain':True,'C_acceptance_digest':rows[1]['digest'],'C_arm_digest':rows[3]['digest'],'C_opaque_receipt_sha256':digest(status['receipt']),'C_private_S1_exported':False}))
'''
 c=json.loads(remote.run('@C_SSH_HOST@',C,45));B='INSTALLED='+repr(b['live']['B'])+'\nCFG='+repr(cfg)+'\n'+r'''
import pathlib,json,subprocess,hashlib,time
p=dict(x.split('=',1) for x in subprocess.check_output(['systemctl','show',INSTALLED['activation_manifest']['unit'],'--property=MainPID,ActiveState,SubState,NRestarts'],text=True,timeout=5).splitlines());assert p['ActiveState']=='active' and p['SubState']=='running' and p['NRestarts']=='0';root=pathlib.Path('/proc')/p['MainPID']/'root';cfg=json.loads((root/'lifecycle'/CFG['run_id']/'config.json').read_bytes());assert cfg['run_id']==CFG['run_id'] and cfg['execution_authorized'] and cfg['terminal_execution_authorized'];out=root/'work/final-qualification/autonomous-results'/cfg['run_id'];events=json.loads((out/'controller.json').read_bytes())['events'];assert [x['kind'] for x in events]==['B_CONTROLLER_STARTED_BEFORE_ACCEPTANCE','B_ARMED_AFTER_C_RECEIPT'];assert not any((out/n).exists() for n in ['boundary-error.json','result.json','C-delivery-failed.json']);arm=json.loads((out/'arm-attempt.json').read_bytes());assert arm['run_id']==cfg['run_id'] and arm['one_attempt'] is True
for n,h in INSTALLED['activation_manifest']['source_pins'].items():assert hashlib.sha256((root/'software'/n).read_bytes()).hexdigest()==h
for name,key in [('old-S0-locator.json','locator'),('pre-funding-checkpoint.json','checkpoint')]:assert json.loads((out/name).read_bytes())==cfg[key]
print(json.dumps({'passed':True,'run_id':cfg['run_id'],'at':time.time(),'B_explicit_ARMED':True,'B_arm_digest':events[1]['payload']['arm_digest'],'B_receipt_sha256':arm['receipt_sha256'],'no_A_dependency_after_boundary':True}))
'''
 br=json.loads(remote.run('@B_SSH_HOST@',B,30));assert br['B_arm_digest']==c['C_arm_digest'] and br['B_receipt_sha256']==c['C_opaque_receipt_sha256'];value={'C':c,'B':br,'at':time.time(),'passed':True,'poweroff_performed':False};durable(E/'final-poweroff-check-finite.json',value);return value
