from pathlib import Path
import sys,os,json,hashlib,subprocess,tempfile,time
O=Path(__file__).resolve().parent;BASE=Path('@KPI_REPO@/.local/g5-preparation');E=O/'live-execution'
TRANSPORT=BASE/'orchestrator-dedicated-B-fresh-preparation-20261007T045400Z/dedicated_remote.py'
assert hashlib.sha256(TRANSPORT.read_bytes()).hexdigest()=='131624eadf5f275abc5bb866980db268596092525820c9aae3b62ad5cc1d4d96'
sys.path.append(str(TRANSPORT.parent));import dedicated_remote as remote
assert Path(remote.__file__).resolve()==TRANSPORT.resolve()
NODE=Path('@KPI_HOME@/.nvm/versions/node/v22.22.3/bin/node')
SDK=BASE.parent/'sdk/kaspa-wasm32-sdk/nodejs/kaspa'
CROOT='/opt/kpi-recovery-admin/audit/orchestrator-finite-launch-preparation-20261007T101055Z/finite-launcher'

def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def durable(p,value):
    p=Path(p);raw=value if isinstance(value,bytes) else json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    with p.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno());os.fchmod(f.fileno(),0o600)
    fd=os.open(p.parent,os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    return sha(p)
def clean_env():
    return {'PATH':str(NODE.parent)+':/usr/bin:/bin','LANG':'C.UTF-8','XDG_RUNTIME_DIR':'/run/user/'+str(os.getuid()),'DBUS_SESSION_BUS_ADDRESS':'unix:path=/run/user/'+str(os.getuid())+'/bus','PYTHONDONTWRITEBYTECODE':'1','RAYON_NUM_THREADS':'2'}

def c_call(q,timeout=150):
    # Each remote invocation re-verifies the administrative package, then spawns
    # the same isolated process for startup tests and actual live acquisition.
    pins=read(O/'launcher-hashes.json')['C_package']
    code='PINS='+repr(pins)+'\nROOT='+repr(CROOT)+'\nQ='+repr(q)+'\n'+r'''
import pathlib,hashlib,subprocess,json
for n,h in PINS.items():
 p=pathlib.Path(ROOT)/n;assert p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==h,'C launcher package pin mismatch'
p=subprocess.run(['/usr/bin/env','-i','PATH=/usr/bin:/bin','LANG=C.UTF-8','/usr/bin/python3','-I',ROOT+'/c_helper.py'],input=json.dumps(Q).encode(),capture_output=True,timeout=140)
try:r=json.loads(p.stdout)
except Exception:raise ValueError('C helper returned no complete receipt')
print(json.dumps(r));assert p.returncode==0,r
'''
    return json.loads(remote.run('@C_SSH_HOST@',code,timeout))
def sdk_read(q,folder):
    p=Path(folder)/('sdk-read-'+str(time.time_ns())+'.private.json');durable(p,dict(q,sdkDir=str(SDK)))
    proc=subprocess.run([str(NODE),str(O/'sdk_readonly.mjs'),str(p)],env=clean_env(),capture_output=True,text=True,timeout=22)
    r=json.loads(proc.stdout)
    if proc.returncode or not r.get('passed'):raise ValueError('SDK read-only probe rejected: '+r.get('reason','unknown'))
    return r

def wallet_context(folder,endpoint,run_id):
    from rpc_contract import validate_submission_route
    validate_submission_route(endpoint,run_id)
    p=BASE.parent.parent/'.env.tn10.local';assert p.stat().st_mode&0o777==0o600
    import re
    env={}
    for line in p.read_text().splitlines():
        m=re.match(r'^\s*([A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*$',line)
        if m:env[m[1]]=m[2].strip('"\'')
    assert env['KASPA_NETWORK']=='tn10'
    result=c_call({'action':'wallet','address':env['KPI_FUNDING_ADDRESS']},45)
    sdk=sdk_read({'action':'fees','url':'ws://127.0.0.1:29211','node_p2p_identity_sha256':endpoint['SDK_probe']['node_p2p_identity_sha256']},folder)
    assert result['server']['networkId']==sdk['server']['networkId']=='testnet-10'
    result['fees']=sdk['fees'];guard=result.pop('guard_dir')
    durable(Path(folder)/'wallet-context-refreshed.json',result);durable(Path(folder)/'runtime-stage.json',{'guard_dir':guard})
    return {'passed':True,'RPC_contract_matched':True,'SDK_fee_capability_matched':True,'wallet_cardinality':len(result['utxos']['entries']),'submit_RPC_invoked':False}

def checkpoint_seal(folder,run_id,scope):
    target='/opt/kpi-recovery-admin/audit/'+O.name+'/'+scope+'/'+run_id+'-'+str(time.time_ns())
    v=c_call({'action':'checkpoint','output':target})
    raw=v.pop('checkpoint_raw').encode();assert hashlib.sha256(raw).hexdigest()==v['receipt']['checkpoint_sha256']
    durable(Path(folder)/'pre-funding-checkpoint.json',raw);durable(Path(folder)/'C-prefunding-checkpoint-acquisition.json',v)
    return v
