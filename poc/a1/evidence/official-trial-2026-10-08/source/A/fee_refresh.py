"""Read-only finite-run adapter for the unchanged original fee/native/SDK gate.
No RPC submit operation. No historical quote relabeling. Nothing runs on import.
"""
import argparse,hashlib,json,os,pathlib,subprocess
P=pathlib.Path;OUT=P(__file__).resolve().parent
BASE=P('@KPI_REPO@/.local/g5-preparation')
QUALIFIED='2590e392ef97af6ea81aa8fc177a3996a7fa93a7';PUBLICATION='575d0e93afdb9d5f522d9fd5500026f3ca2ba018'
SOURCE_SHA='09c4def9786a691153c7f8311d5a5f3053eb022de2211151dbff88959adf99b7'
EQUIVALENCE_SHA='7159c0103db0e1e368d7b43d0263284d27cb09cfda4e4766252ae5987d5864db'
def require(x,m):
 if not x:raise ValueError(m)
def sha(p):return hashlib.sha256(P(p).read_bytes()).hexdigest()
def once(text,old,new):
 require(text.count(old)==1,'original fee adapter exact source mismatch');return text.replace(old,new)
def adapt(raw):
 require(hashlib.sha256(raw).hexdigest()==SOURCE_SHA,'original fee source changed');s=raw.decode()
 s=once(s,'import remote\n','from launcher_common import remote\n')
 old="p=subprocess.run([str(x) for x in args],capture_output=True,timeout=180);require(p.returncode==0,'pinned read-only fee/SDK check failed (details retained privately)');output.write_bytes(p.stdout)"
 new="""p=subprocess.run([str(x) for x in args],capture_output=True,timeout=180)
 for suffix,raw in [('.child.stdout',p.stdout),('.child.stderr',p.stderr)]:
  target=pathlib.Path(str(output)+suffix);fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 require(p.returncode==0,'pinned read-only fee/SDK check failed (exact child diagnostics retained privately)');output.write_bytes(p.stdout)"""
 s=once(s,old,new)
 s=once(s,"A1/'scripts/a1_fee_check.py'","pathlib.Path(__file__).resolve().parent/'fee_policy_adapter.py'")

 s=once(s,'ROOT=pathlib.Path(__file__).resolve().parents[1];A1=', 'ROOT=pathlib.Path('+repr(str(BASE))+');A1=')
 old="require(subprocess.check_output(['git','-C',str(A1),'rev-parse','HEAD'],text=True).strip()==PINS['pr22_head'],'source changed')"
 s=once(s,old,"require(PINS['pr22_head']==QUALIFIED and subprocess.check_output(['git','-C',str(A1),'rev-parse','HEAD'],text=True).strip()==PUBLICATION,'reviewed repository identity changed')")
 old="sys.path.insert(0,'/opt/kpi-g5-capture');from rpc_local import RPC"
 new="""root=pathlib.Path(INSTALLED['source_root'])
for n,h in INSTALLED['source_pins'].items():
 p=root/n;assert p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==h
p=pathlib.Path(INSTALLED['config_path']);assert not p.is_symlink();raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==INSTALLED['config_sha256'];cfg=json.loads(raw)
sys.path.insert(0,str(root));from rpc_local import RPC;from finite_runtime import settings,node_binding
settings(cfg);node_binding(cfg)"""
 s=once(s,old,new)
 s=once(s,"policy=json.loads(remote.run('@C_SSH_HOST@',code,90));", "code='INSTALLED='+repr(INSTALLED)+'\\n'+code\npolicy=json.loads(remote.run('@C_SSH_HOST@',code,90));")
 # Raw quotes and node policy are retained before original a1_fee_check rejects.
 # The qualified implementation already writes C-policy.json before that call.
 # Also retain the exact RPC response before any original policy guard rejects.
 marker="require(policy['node_binary_sha256']==baseline['node_binary_sha256'],'target binary changed; requalify')"
 s=once(s,marker,"diagnostics=pathlib.Path(__file__).resolve().parent/'fee-diagnostics';diagnostics.mkdir(mode=0o700,exist_ok=True);diagnostic=diagnostics/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'.json')\nfd=os.open(diagnostic,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)\nwith os.fdopen(fd,'w') as f:json.dump(policy,f,sort_keys=True);f.flush();os.fsync(f.fileno())\n"+marker)
 compile(s,str(OUT/'qualified-fee-preflight.py'),'exec');return s

def verify_equivalence():
 require(sha(OUT/'implementation-equivalence.json')==EQUIVALENCE_SHA,'original implementation receipt changed');r=json.loads((OUT/'implementation-equivalence.json').read_bytes())
 require(r['implementation_equivalence']=='PASS' and r['qualified_implementation_commit']==QUALIFIED and r['current_repository_publication_HEAD']==PUBLICATION,'implementation identity')
 repo=BASE.parent/'worktrees/a1-poc';require(subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True,timeout=5).strip()==PUBLICATION,'publication HEAD changed')
 for row in r['compared_paths']:
  if row['security_critical_input']:
   p=repo/row['path'];require(row['identical'] and p.is_file() and not p.is_symlink() and sha(p)==row['qualified_sha256']==row['publication_sha256'] and bool(p.stat().st_mode&0o111)==(row['publication_mode']=='100755'),'qualified implementation changed')

def run(binding_path,binding_sha):
 require(sha(binding_path)==binding_sha,'external installed binding hash');b=json.loads(P(binding_path).read_bytes());cfg=json.loads((OUT/'planned-live-config.private.json').read_bytes())
 require(b['schema']=='kpi-finite-installed-runtime-binding/v1' and b['planned_live_run_id']==cfg['run_id'] and b['network']=='testnet-10','new finite fee run binding')
 require(b['C']['execution_authorized'] is False and b['C']['terminal_execution_authorized'] is False,'fee preparation standby only')
 verify_equivalence();text=adapt((OUT/'qualified-fee-preflight.py').read_bytes());os.umask(0o077)
 namespace={'__file__':str(OUT/'qualified-fee-preflight.py'),'__name__':'__main__','QUALIFIED':QUALIFIED,'PUBLICATION':PUBLICATION,'INSTALLED':b['C']}
 exec(compile(text,str(OUT/'qualified-fee-preflight.py'),'exec'),namespace)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--runtime-binding',required=True);p.add_argument('--runtime-binding-sha256',required=True);a=p.parse_args();run(a.runtime_binding,a.runtime_binding_sha256)
