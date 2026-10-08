"""Mandatory bounded pre-funding endpoint gate. Never submits a transaction."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, sys, tempfile, time
OUT = Path(__file__).resolve().parent
BASE = Path('@KPI_REPO@/.local/g5-preparation')
sys.path.insert(0, str(BASE))
from launcher_common import remote
URL = 'ws://127.0.0.1:29211'
UNIT = 'kpi-g5-prepared-funding-link.service'
NODE = Path('@KPI_HOME@/.nvm/versions/node/v22.22.3/bin/node')
SDK = BASE.parent / 'sdk/kaspa-wasm32-sdk/nodejs/kaspa'
NODE_SHA = 'e6ec2c188d83d813f81f2de8aea084d74dce603ac1abedd0a30ad941b10087b2'

class EndpointError(ValueError):
    pass

def require(value, message):
    if not value:
        raise EndpointError(message)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def check(run_id=None,installed_binding=None):
    require(installed_binding is not None,'explicit installed finite binding required')
    require(installed_binding['planned_live_run_id']==run_id and installed_binding['network']=='testnet-10','finite endpoint identity')
    require(sha(NODE) == NODE_SHA, 'pinned Node runtime changed')
    pins = json.loads((BASE/'source-pins.json').read_bytes())
    for n,v in pins['SDK']['files'].items():
        require(sha(SDK/n) == v['sha256'], 'pinned SDK changed')
    argv = json.loads((OUT/'qualified-funding-ssh-command.private.json').read_bytes())['argv']
    require(argv[-1] == remote.target_C() and argv[-3:-1] == ['-L','127.0.0.1:29211:127.0.0.1:18210'], 'unqualified endpoint route')
    props = dict(x.split('=',1) for x in subprocess.check_output(['systemctl','--user','show',UNIT,'--property=ActiveState,SubState,MainPID,NRestarts'],text=True,timeout=5).splitlines())
    require(props['ActiveState']=='active' and props['SubState']=='running' and props['MainPID']!='0', 'funding SSH service not running')
    pid=props['MainPID']
    actual=[x.decode() for x in Path('/proc',pid,'cmdline').read_bytes().split(b'\0') if x]
    require(actual==argv, 'stale or substituted forwarding process')
    listeners=subprocess.check_output(['ss','-ltnpH','( sport = :29211 )'],text=True,timeout=5).splitlines()
    require(len(listeners)==1 and listeners[0].split()[3]=='127.0.0.1:29211' and ('pid='+pid+',') in listeners[0], 'no qualified TCP listener')
    code=r'''import pathlib,subprocess,hashlib,json,sys,time
root=pathlib.Path(INSTALLED['source_root'])
for n,h in INSTALLED['source_pins'].items():
 p=root/n;assert p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==h
p=pathlib.Path(INSTALLED['config_path']);assert not p.is_symlink();raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==INSTALLED['config_sha256'];cfg=json.loads(raw)
sys.path.insert(0,str(root));from rpc_local import RPC;from finite_runtime import settings,node_binding
settings(cfg);node_binding(cfg)
unit=dict(x.split('=',1) for x in subprocess.check_output(['systemctl','show','kpi-tn10.service','--property=ActiveState,SubState,MainPID,NRestarts'],text=True).splitlines())
assert unit['ActiveState']=='active' and unit['SubState']=='running';pid=unit['MainPID']
binary=hashlib.sha256(pathlib.Path('/proc',pid,'exe').read_bytes()).hexdigest();assert binary=='adf711b68abb2fabbb33cfdaab8f915bb615f8d7d1b33a867328b4672ddd376f'
args=pathlib.Path('/proc',pid,'cmdline').read_bytes().split(b'\0');assert b'--rpclisten-json=127.0.0.1:18210' in args
lines=subprocess.check_output(['ss','-ltnpH','( sport = :18210 )'],text=True).splitlines();assert len(lines)==1 and lines[0].split()[3]=='127.0.0.1:18210' and ('pid='+pid+',') in lines[0]
r=RPC();r.METHODS=set(r.METHODS)|{'getInfo'}
try:server=r.call('getServerInfo',{});info=r.call('getInfo',{})
finally:r.close()
print(json.dumps({'at':time.time(),'server':server,'info':info,'node_binary_sha256':binary,'node_unit':unit,'native_JSON_RPC_listener_owned_by_node':True,'native_JSON_RPC_direct_unfiltered_route':True,'submit_RPC_invoked':False}))'''
    code='INSTALLED='+repr(installed_binding['C'])+'\n'+code
    witness=json.loads(remote.run('@C_SSH_HOST@',code,20))
    input={'url':URL,'expectedUrl':URL,'witness':witness,'sdkDir':str(SDK),'timeoutMs':5000}
    with tempfile.TemporaryDirectory(prefix='endpoint-read-',dir=OUT) as td:
        p=Path(td)/'input.json';p.write_text(json.dumps(input));p.chmod(0o600)
        child=subprocess.run([str(NODE),str(OUT/'endpoint_sdk_probe.mjs'),str(p)],capture_output=True,text=True,timeout=22)
        try:result=json.loads(child.stdout)
        except (ValueError,TypeError):raise EndpointError('SDK endpoint probe failed without a complete receipt')
        require(child.returncode==0 and result.get('passed') is True, result.get('blocker','SDK endpoint probe rejected'))
    # Catch replacement or loss between the SDK probe and issuing the receipt.
    after=dict(x.split('=',1) for x in subprocess.check_output(['systemctl','--user','show',UNIT,'--property=ActiveState,SubState,MainPID,NRestarts'],text=True,timeout=5).splitlines())
    require(after==props, 'funding SSH process changed during readiness')
    listeners_after=subprocess.check_output(['ss','-ltnpH','( sport = :29211 )'],text=True,timeout=5).splitlines()
    require(listeners_after==listeners, 'funding listener changed during readiness')
    require(-2<=time.time()-witness['at']<=15, 'stale endpoint witness')
    if run_id is not None:
        require(run_id==json.loads((OUT/'planned-live-config.private.json').read_bytes())['run_id'], 'wrong readiness run ID')
    return {'schema':'kpi-prefunding-endpoint-readiness/v1','at':time.time(),'expiry_seconds':30,'run_id':run_id,'passed':True,'endpoint':URL,'tunnel_unit':UNIT,'tunnel_process':props,'C_node_process':witness['node_unit'],'C_node_binary_sha256':witness['node_binary_sha256'],'SDK_probe':result,'funding':False,'broadcast':False,'submit_RPC_invoked':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime-binding',type=Path,required=True);p.add_argument('--runtime-binding-sha256',required=True);p.add_argument('--run-id');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    os.umask(0o077)
    try:
        require(sha(a.runtime_binding)==a.runtime_binding_sha256,'externally bound runtime changed');result=check(a.run_id,json.loads(a.runtime_binding.read_bytes()))
    except Exception as exc:
        # Fail closed; private SSH target/stderr/credentials are never printed.
        result={'schema':'kpi-prefunding-endpoint-readiness/v1','at':time.time(),'run_id':a.run_id,'passed':False,'blocker':str(exc) if isinstance(exc,EndpointError) else type(exc).__name__,'funding':False,'broadcast':False,'submit_RPC_invoked':False}
    raw=json.dumps(result,sort_keys=True,separators=(',',':')).encode()
    with a.output.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    print(json.dumps(result,indent=2))
    sys.exit(0 if result['passed'] else 1)
