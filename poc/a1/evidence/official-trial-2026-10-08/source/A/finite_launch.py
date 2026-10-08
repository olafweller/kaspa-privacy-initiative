from fixed_terms import u64
"""Finite A orchestration over retained qualified wallet/worker entrypoints.
Only actual no-submit startup-check is exposed. No live transaction phase is
implemented or accepted. No original Q main is executed.
"""
import argparse,hashlib,json,os,pathlib,subprocess,sys,time
HERE=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from launcher_common import BASE,E,NODE,read,sha,durable,clean_env,remote
import controller_access as ca

def require(ok,why):
 if not ok:raise ValueError(why)
def encode(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def config():
 cfg=read(HERE/'planned-live-config.private.json');require(cfg['mode']=='finite-live-native' and all(cfg.get(k) is False for k in ['execution_authorized','terminal_execution_authorized','funding_authorized','poweroff_authorized']),'false-authority finite plan')
 contract=read(HERE/'HELPER-SOURCE-CONTRACT.json')
 require(cfg['worker_source_sha256']==contract['genuine_worker_source_sha256'] and cfg['worker_files_sha256']==contract['genuine_worker_files_sha256'],'actual A worker identity')
 for n,h in cfg['worker_files_sha256'].items():require(sha(BASE/'boundary-final'/n)==h,'actual qualified A worker file')
 for n,h in (contract['effective']|contract['new_local_entrypoints']).items():require(sha(HERE/n)==h,'finite helper source changed')
 return cfg

def binding(path,pin,cfg):
 require(sha(path)==pin,'external runtime binding hash');b=read(path)
 require(b['schema']=='kpi-finite-installed-runtime-binding/v1' and b['planned_live_run_id']==cfg['run_id'] and b['network']=='testnet-10','installed finite identity')
 require(b['source_contract_sha256']==sha(HERE/'HELPER-SOURCE-CONTRACT.json'),'installed helper contract')
 for role in ['B','C']:
  require(b[role]['run_id']==b['standby_run_id'] and b[role]['execution_authorized'] is False and b[role]['terminal_execution_authorized'] is False,'unfunded installed standby')
 require(b['C']['config']['worker_source_sha256']==cfg['worker_source_sha256'] and b['C']['config']['worker_files_sha256']==cfg['worker_files_sha256'],'standby real A worker binding')
 require(b['C']['config']['finite']['watch_addresses'][-1]==read(pathlib.Path(read(HERE/'live-candidate-run-location.private.json')['path'])/'public/manifest.json')['recipient']['address'],'predeclared payout watch')
 return b

def authority(path,pin,cfg,b,checklist_path=None):
 # This JSON is provisioned only after a later user authorization. An old run,
 # checklist, preparation receipt, or B request cannot supply this authority.
 require(sha(path)==pin,'explicit authority hash');a=read(path);checklist_path=pathlib.Path(checklist_path) if checklist_path is not None else HERE/'immutable-run-checklist.json';check=read(checklist_path)
 required={'schema','run_id','network','explicit_live_start_authorization','checklist_sha256','runtime_binding_sha256','funding_attempts','continuation_attempts','terminal_attempts','max_wallet_debit_sompi','max_funding_fee_sompi','terminal_exit_broadcast_authorized'}
 require(set(a)==required and a['schema']=='kpi-finite-exact-user-live-authorization/v1' and a['run_id']==cfg['run_id'] and a['network']=='testnet-10' and a['explicit_live_start_authorization'] is True,'new exact live authority required')
 require(a['checklist_sha256']==sha(checklist_path) and a['runtime_binding_sha256']==hashlib.sha256(encode(b)).hexdigest(),'authority preparation bindings')
 require(all(type(a[k]) is int and a[k]==1 for k in ['funding_attempts','continuation_attempts','terminal_attempts']) and u64(a['max_wallet_debit_sompi'])==u64(check['fixed_terms']['maximum_wallet_debit_sompi']) and u64(a['max_funding_fee_sompi'])==u64(check['fixed_terms']['funding_fee_cap_sompi']) and a['terminal_exit_broadcast_authorized'] is True,'exact one-attempt monetary authority')
 require(check['schema']=='kpi-finite-live-run-checklist/v1' and check['run_id']==cfg['run_id'] and check['worker_source_sha256']==cfg['worker_source_sha256'] and check['runtime_binding_sha256']==a['runtime_binding_sha256'] and check['preparation_ready_for_live'] is True,'concrete reviewed live checklist')
 return a

def query(cfg,op,extra=None,binding=None):
 b=binding if binding is not None else read(E/'installed-runtime-binding.json')
 args,raw=ca.transport_for(cfg,b,op,extra)
 p=subprocess.run(args,input=raw,capture_output=True,timeout=150);require(p.returncode==0,'new forced controller route rejected');r=json.loads(p.stdout);require('error' not in r,'controller rejected');return r

def startup(cfg,b):
 standby=dict(cfg,run_id=b['standby_run_id']);checkpoint=query(standby,'finite-checkpoint',binding=b);require(checkpoint['seq']>=0,'actual finite observer checkpoint');s=query(standby,'status',binding=b)
 require(s['run_id']==standby['run_id'] and s['mode']=='finite-live-native' and s['faulted'] is False and not s['events'] and s['terminal_result'] is None,'actual unarmed C standby')
 # Actual B source/service/config checks use the running jail namespace, not host /software.
 code='B='+repr(b['B'])+'\n'+r'''
import pathlib,hashlib,json,subprocess,time
p=dict(x.split('=',1) for x in subprocess.check_output(['systemctl','show',B['unit'],'--property=MainPID,ActiveState,SubState,NRestarts'],text=True,timeout=5).splitlines())
assert p['ActiveState']=='active' and p['SubState']=='running' and p['NRestarts']=='0'
root=pathlib.Path('/proc')/p['MainPID']/'root'
for n,h in B['source_pins'].items():assert hashlib.sha256((root/'software'/n).read_bytes()).hexdigest()==h
raw=(root/'lifecycle'/B['run_id']/'config.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==B['config_sha256'];cfg=json.loads(raw);assert all(cfg.get(k) is False for k in ['execution_authorized','terminal_execution_authorized','funding_authorized','poweroff_authorized'])
out=root/'work/final-qualification/autonomous-results'/B['run_id'];assert not any((out/n).exists() for n in ['arm-attempt.json','result.json','boundary-error.json','C-delivery-failed.json'])
print(json.dumps({'passed':True,'run_id':B['run_id'],'unit':B['unit'],'pid':p['MainPID'],'at':time.time()}))
'''
 bv=json.loads(remote.run('@B_SSH_HOST@',code,30));require(bv['passed'] is True,'actual B standby')
 return {'schema':'kpi-finite-actual-startup/v1','run_id':cfg['run_id'],'standby_run_id':standby['run_id'],'at':time.time(),'C_empty_unarmed':True,'B_actual_namespace_sources':True,'B':bv,'funding':False,'broadcast':False,'poweroff':False}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--runtime-binding',required=True);parser.add_argument('--runtime-binding-sha256',required=True);parser.add_argument('action',choices=['startup-check']);args=parser.parse_args()
 cfg=config();b=binding(args.runtime_binding,args.runtime_binding_sha256,cfg)
 print(json.dumps(startup(cfg,b),sort_keys=True))
