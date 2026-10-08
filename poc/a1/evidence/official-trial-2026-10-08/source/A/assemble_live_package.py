"""Derive final local run bindings/checklist from hash-pinned actual receipts.
No SSH, systemd, authorization generation, funding or transaction operations.
The inspected installer descriptor remains immutable; output is a fresh child.
"""
import argparse,copy,hashlib,json,os,pathlib,re
from build_install_manifest import build
from finite_install import unix_path
from fixed_terms import check_credit_policy
P=pathlib.Path;HERE=P(__file__).resolve().parent

def require(v,m):
 if not v:raise ValueError(m)
def encode(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(v):return hashlib.sha256(encode(v)).hexdigest()
def sha(p):return hashlib.sha256(P(p).read_bytes()).hexdigest()
def pinned(p,h):
 p=P(p);require(p.is_file() and not p.is_symlink() and sha(p)==h,'external artifact pin');return json.loads(p.read_bytes())
def pin(v):require(type(v) is str and re.fullmatch('[0-9a-f]{64}',v) is not None,'exact SHA256 required');return v

def assemble(b,contract,contract_sha,terms,receipts,builder,builder_sha):
 require(b['schema']=='kpi-finite-installed-runtime-binding/v1' and b['actual_installed'] is True and b['network']=='testnet-10','actual installed finite descriptor required')
 run=b['planned_live_run_id'];standby=b['standby_run_id'];require(re.fullmatch('[A-Za-z0-9_-]{8,100}',run) and run!=standby,'unused separate planned run')
 require(contract_sha==b['source_contract_sha256'],'final installed A source contract')
 require(terms['schema']=='kpi-native-fixed-term-extraction/v1' and terms['network']=='testnet-10' and terms['live_authorized'] is False,'reviewed fixed terms without authority')
 check_credit_policy(terms['credit_sompi'],terms['branch_fees_sompi'])
 c=b['C']['config'];require(c['manifest_sha256']==terms['manifest_sha256'],'exact generated native BASE')
 require(c['worker_source_sha256']==contract['genuine_worker_source_sha256'] and c['worker_files_sha256']==contract['genuine_worker_files_sha256'],'genuine A worker identity')
 for role in ['B','C']:
  v=b[role];require(v['run_id']==standby and v['unit']=='kpi-finite-'+role.lower()+'-'+standby+'.service','actual role-local standby')
  pin(v['unit_sha256']);require(v['source_pins']==v['config']['effective_role_source_pins'][role],'inspected role source pins')
  require(all(v['config'].get(k) is False for k in ['execution_authorized','terminal_execution_authorized','funding_authorized','poweroff_authorized']),'unfunded standby only')
 s=receipts['startup'];require(s['schema']=='kpi-finite-actual-startup/v1' and s['run_id']==run and s['standby_run_id']==standby and s['C_empty_unarmed'] is True and s['B_actual_namespace_sources'] is True and s['B']['passed'] is True,'actual complete startup receipt')
 e=receipts['endpoint'];require(e['schema']=='kpi-prefunding-endpoint-readiness/v1' and e['run_id']==run and e['passed'] is True and e['submit_RPC_invoked'] is False,'actual endpoint no-submit receipt')
 fee=receipts['fee'];require(fee['run_id']==run and fee['passed'] is True and fee['funding_authorized'] is False and fee['native_full_revalidated'] is True and fee['fixed_terms_not_changed'] is True,'actual exact BASE fee/native/SDK receipt')
 # The receipts prove these preparation mechanisms at their recorded times.
 # The future launcher independently repeats current endpoint/fee/node gates.
 out=copy.deepcopy(b);out['B_expectations_builder']=str(P(builder).resolve());out['B_expectations_builder_sha256']=pin(builder_sha);out['live']={}
 for role in ['B','C']:
  v=b[role];root=('/opt/kpi-finite-live/' if role=='C' else '/srv/kpi-recovery/finite-live/')+run;
  if role=='C':unix_path(root+'/socket/control.sock')
  admin=v['activation_helper'];pin(v['activation_helper_sha256']);require(v['activation_helper_sha256']==sha(HERE/'finite_live_activate.py'),'inspected staged activation helper')
  require(v['activation_support_pins']=={n:sha(HERE/n) for n in ['finite_install.py','fixed_terms.py']},'inspected activation imports')
  cfg=copy.deepcopy(v['config']);cfg['run_id']=run
  if role=='C':cfg['finite']['root']=root+'/finite-runs';cfg['terminal_policy']['run_id']=run
  artifact=build(role,cfg,digest(cfg),v['source_root'],root,credential_root=v.get('credentials'),credential_pins=v.get('credential_pins'))
  m=artifact['manifest'];m.update(standby_run_id=standby,new_standby_units={role:{'unit':v['unit'],'unit_sha256':v['unit_sha256']}})
  if role=='C':
   require(type(b['C_authorized_keys_uid']) is int,'inspected key-file owner');m.update(authorized_keys_path=b['C_authorized_keys_path'],authorized_keys_preimage_sha256=pin(b['C_authorized_keys_after_sha256']),authorized_keys_uid=b['C_authorized_keys_uid'],route_keys=[])
   require({x['role'] for x in b['route_keys']}=={'B','controller'},'two installed source-restricted routes')
   for x in b['route_keys']:
    raw=x['forced_line'];require(type(raw) is str and raw.endswith('\n') and raw.count('\n')==1 and hashlib.sha256(raw.encode()).hexdigest()==x['forced_line_sha256'],'exact newline-inclusive installed key row')
    require(re.search(r'(?:^|,)from="[^"]+"',raw) is not None,'inspected source restriction')
    public=' '.join(x['public_key'].split()[:2]);require(public in raw,'installed credential row');m['route_keys'].append({'role':x['role'],'public_key':public,'standby_line_sha256':hashlib.sha256(raw[:-1].encode()).hexdigest()})
  else:require(type(v['credential_pins']) is dict and set(v['credential_pins'])=={'access.json','id_ed25519','known_hosts'},'actual credential file pins')
  out['live'][role]={'source_root':v['source_root'],'state_root':root,'activation_helper':admin,'activation_helper_sha256':v['activation_helper_sha256'],'activation_support_pins':v['activation_support_pins'],'activation_manifest':m}
 check={'schema':'kpi-finite-live-run-checklist/v1','network':'testnet-10','run_id':run,'standby_run_id':standby,'preparation_ready_for_live':True,'manifest_sha256':c['manifest_sha256'],'inventory_sha256':c['inventory_sha256'],'worker_source_sha256':c['worker_source_sha256'],'worker_files_sha256':c['worker_files_sha256'],'source_contract_sha256':contract_sha,'fixed_terms':terms,'fixed_terms_sha256':digest(terms),'runtime_binding_sha256':digest(out),'installed_runtime_binding_sha256':digest(out),'prefunding_endpoint_readiness':{'endpoint':'ws://127.0.0.1:29211','checker_sha256':sha(HERE/'endpoint_readiness.py'),'SDK_probe_sha256':sha(HERE/'endpoint_sdk_probe.mjs')},'qualification_scope':'Actual recorded no-submit startup and BASE source/native/SDK/fee/endpoint preparation; fresh live gates repeated automatically; no future transaction admission claimed','qualification_receipts_sha256':{k:digest(v) for k,v in receipts.items()},'funding_authorized':False,'terminal_execution_authorized':False,'poweroff_authorized':False}
 return out,check

def write(p,value):
 raw=encode(value);fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 return hashlib.sha256(raw).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for k in ['binding','terms','startup','endpoint','fee']:
  p.add_argument('--'+k,required=True);p.add_argument('--'+k+'-sha256',required=True)
 p.add_argument('--builder',required=True);p.add_argument('--builder-sha256',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 b=pinned(a.binding,a.binding_sha256);terms=pinned(a.terms,a.terms_sha256);contract=json.loads((HERE/'HELPER-SOURCE-CONTRACT.json').read_bytes())
 for n,h in (contract['effective']|contract['new_local_entrypoints']).items():require(sha(HERE/n)==h,'frozen A helper source')
 require(sha(a.builder)==a.builder_sha256,'actual independent B expectations builder');receipts={k:pinned(getattr(a,k),getattr(a,k+'_sha256')) for k in ['startup','endpoint','fee']}
 binding,check=assemble(b,contract,sha(HERE/'HELPER-SOURCE-CONTRACT.json'),terms,receipts,a.builder,a.builder_sha256)
 output=P(a.output);require(output.parent.is_dir() and not output.exists(),'fresh local output child');output.mkdir(mode=0o700)
 result={n:write(output/n,v) for n,v in [('installed-runtime-binding.json',binding),('immutable-run-checklist.json',check)]}
 fd=os.open(output,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 print(json.dumps({'output':str(output.resolve()),'sha256':result,'live_authority_generated':False,'remote_actions':False}))
if __name__=='__main__':main()
