"""Immediate deterministic binding to authenticated fresh C checkpoint, no services/keys."""
from pathlib import Path
import json,hashlib,sys,os,base64
W=Path(__file__).resolve().parent;T=W.parent;P=T/'package-standby-cwd';Q=Path('@KPI_REPO@/.local/g5-preparation/orchestrator-dedicated-B-fresh-preparation-20261007T045400Z');sys.path.insert(0,str(Q));import dedicated_remote,remote_safety
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();enc=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def save(p,v):
 with Path(p).open('xb') as f:os.fchmod(f.fileno(),0o600);f.write(enc(v));f.flush();os.fsync(f.fileno())
def execute():
 release=json.loads((W/'ROOT-STANDBY-CWD-RELEASE.json').read_bytes());assert release['bind_source_sha256']==sha(__file__);plan=json.loads((P/'STAGE-PLAN.json').read_bytes());assert sha(P/'STAGE-PLAN.json')==release['plan_sha256'];pref=json.loads((W/'C-standby-cwd-prefund-actual.private.json').read_bytes());assert pref['passed'];expected=pref['helper'];root=plan['C_root']
 code='ROOT='+repr(root)+'\n'+r'''
import pathlib,json,base64
r=pathlib.Path(ROOT);print(json.dumps({'config':base64.b64encode((r/'state/config.json').read_bytes()).decode()}))
'''
 raw=json.loads(dedicated_remote.run('@C_SSH_HOST@',remote_safety.wrap(code,'C','standby-fix-bind-readonly'),20));cfgraw=base64.b64decode(raw['config'],validate=True);assert hashlib.sha256(cfgraw).hexdigest()==expected['config_sha256'];cfg=json.loads(cfgraw);assert cfg['run_id']==plan['standby_run_id'] and all(cfg[k] is False for k in ['execution_authorized','terminal_execution_authorized','funding_authorized','poweroff_authorized']);save(P/'C/config.json',cfg)
 keys=json.loads((W/'STANDBY-ROUTE-KEYS.private.json').read_bytes());old=json.loads((W/'STANDBY-INSTALL-BINDING.private.json').read_bytes());b=json.loads((P/'B/config.template.json').read_bytes());b['checkpoint']=cfg['checkpoint'];b['finite_expected']={'schema':'kpi-B-finite-expectations/v1','run_id':cfg['run_id'],'network':'testnet-10','genesis':cfg['finite']['genesis'],'server_version':cfg['finite']['server_version'],'config_sha256':hashlib.sha256(enc({k:v for k,v in cfg.items() if k not in ['checkpoint','locator']})).hexdigest(),'role_sources_sha256':hashlib.sha256(enc(cfg['finite']['role_sources'])).hexdigest(),'native_sha256':cfg['finite']['native']['sha256'],'sdk_sha256':cfg['finite']['sdk']['sha256'],'checkpoint_sha256':hashlib.sha256(enc(cfg['checkpoint'])).hexdigest()};save(P/'B/config.json',b)
 sys.path.insert(0,str(P/'C'));from build_install_manifest import build
 outputs={}
 for role,c in [('C',cfg),('B',b)]:
  pin=sha(P/role/'config.json');outputs[role]=build(role,c,pin,plan[role+'_source_root'],plan[role+'_state_root'],credential_root=plan['B_credential_root'],credential_pins=keys['B_credential_pins'],prefund=expected['prefund_sha256'],prefund_seal=expected['prefund_seal_sha256']);save(P/role/'install-output.json',outputs[role]);save(P/role/'install-manifest.json',outputs[role]['manifest'])
 lines={}
 for k,pub in keys['public_keys'].items():
  peer=keys['peers'][k];command=outputs['C']['forced_commands'][k];assert '"' not in command;lines[k]='restrict,from="'+peer+'",command="'+command+'" '+pub+'\n'
 save(W/'STANDBY-CWD-ROUTE-KEYS.private.json',dict(keys,lines=lines))
 binding=dict(old,standby_run_id=cfg['run_id'],planned_live_run_id=plan['planned_live_run_id'],source_contract_sha256=sha(T/'package/A/HELPER-SOURCE-CONTRACT.json'),actual_installed=False)
 for role,c in [('C',cfg),('B',b)]:
  binding[role]=dict(old[role],run_id=cfg['run_id'],unit=outputs[role]['manifest']['unit'],config_sha256=sha(P/role/'config.json'),config=c,source_root=plan[role+'_source_root'],source_pins=c['effective_role_source_pins'][role],unit_sha256=hashlib.sha256(outputs[role]['unit'].encode()).hexdigest())
 binding['B'].update(credentials=plan['B_credential_root'],credential_pins=keys['B_credential_pins'])
 binding['A_credential_root']=str(Path(old['A_controller_route']['key']).parent)
 helper_contract=json.loads((T/'package/A/HELPER-SOURCE-CONTRACT.json').read_bytes())
 for role in ['B','C']:
  binding[role]['activation_helper']=plan[role+'_root']+'/admin/finite_live_activate.py'
  binding[role]['activation_helper_sha256']=sha(T/'package/A/finite_live_activate.py')
  binding[role]['activation_support_pins']={n:sha(T/'package/A'/n) for n in ['finite_install.py','fixed_terms.py']}
 binding['C'].update(config_path=outputs['C']['manifest']['config'],socket_root=outputs['C']['manifest']['socket_root']);binding['A_controller_route']=dict(old['A_controller_route'],run_id=cfg['run_id'],config_sha256=sha(P/'C/config.json'),forced_command_sha256=outputs['C']['forced_command_sha256']['controller']);binding['route_keys']=[{'role':k,'public_key':keys['public_keys'][k],'forced_line':line,'forced_line_sha256':hashlib.sha256(line.encode()).hexdigest()} for k,line in lines.items()];save(W/'STANDBY-CWD-INSTALL-BINDING.private.json',binding)
 # C config is C-owned and already retained; stage exactly its derived manifest.
 data=(P/'C/install-manifest.json').read_bytes();code='ROOT='+repr(root)+'\nRAW='+repr(base64.b64encode(data).decode())+'\nPIN='+repr(hashlib.sha256(data).hexdigest())+'\n'+r'''
import pathlib,base64,hashlib,os,json
raw=base64.b64decode(RAW,validate=True);assert hashlib.sha256(raw).hexdigest()==PIN
with (pathlib.Path(ROOT)/'state/install-manifest.json').open('xb') as f:os.fchown(f.fileno(),0,986);os.fchmod(f.fileno(),0o600);f.write(raw);f.flush();os.fsync(f.fileno())
print(json.dumps({'derived_C_manifest_staged':True,'sha256':PIN}))
'''
 save(W/'C-standby-cwd-bound-manifest-stage.private.json',json.loads(dedicated_remote.run('@C_SSH_HOST@',remote_safety.wrap(code,'C','standby-fix-manifest'),20)))
 print('Fresh authenticated checkpoint binding complete; install immediately')
if __name__=='__main__':execute()
