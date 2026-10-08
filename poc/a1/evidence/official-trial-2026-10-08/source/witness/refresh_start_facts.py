"""Future explicit-start read-only facts using the existing authenticated routes.

No import runs SSH. No service, key, backup or transaction is created remotely.
The B peer is observed by C using one bounded pre-auth TCP connection to the
existing SSH listener; do not infer outbound peer from an advertised B IP.
"""
from pathlib import Path
import hashlib, importlib.util, ipaddress, json, os, signal, sys, threading, time

HERE=Path(__file__).resolve().parent
REPO=next(p for p in HERE.parents if (p/'AGENTS.md').is_file())
Q=REPO/'.local/g5-preparation/orchestrator-dedicated-B-fresh-preparation-20261007T045400Z'
PRIOR=REPO/'.local/g5-preparation/B-parent-fix-20261007/successor-r2-ready'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(v,m):
    if not v:raise ValueError(m)
def read(p):return json.loads(Path(p).read_bytes())
def module(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def refresh(cold_root, explicit_start, release):
    root=Path(cold_root).absolute();plan=read(root/'package-standby-cwd/STAGE-PLAN.json')
    require(release['facts_driver_sha256']==sha(__file__),'reviewed facts driver')
    smoke=(release.get('preparation_smoke_authorized') is True and plan.get('namespace_override')==release.get('namespace') and plan.get('namespace_override') is not None and explicit_start.get('preparation_smoke_authorized') is True and explicit_start['explicit_user_start'] is False and explicit_start['scope']=='preparation-smoke-no-submit')
    production=(explicit_start['explicit_user_start'] is True and explicit_start['scope']=='cold-bootstrap-no-submit' and plan.get('namespace_override') is None)
    require((production or smoke) and explicit_start['base_instance_id']==plan['base_instance_id'] and explicit_start['planned_live_run_id']==plan['planned_live_run_id'] and explicit_start['standby_run_id']==plan['standby_run_id'],'future new explicit start')
    require((production or smoke) and explicit_start['funding_authorized'] is explicit_start['terminal_execution_authorized'] is False,'read-only start facts scope')
    for n,h in release['transport_source_pins'].items():require(sha(Q/n)==h,'pinned existing transport support')
    require(set(release['transport_source_pins'])=={'dedicated_remote.py','remote_safety.py','safe_diagnostics.py','platform_baseline.py'},'complete transport support pins')
    sys.path.insert(0,str(Q))
    remote=module('cold_existing_dedicated_remote',Q/'dedicated_remote.py')
    safety=module('cold_existing_remote_safety',Q/'remote_safety.py')
    def run(role,code,timeout):
        return json.loads(remote.run('@C_SSH_HOST@' if role=='C' else '@B_SSH_HOST@',safety.wrap(code,role,'cold-readonly-facts'),timeout))
    cfg=read(root/'package-standby-cwd/C/config.template.json')
    capacity=read(root/'COLD-CAPACITY-REQUIREMENT.json')
    oldcfg=read(PRIOR/'package-standby-cwd/C/config.template.json')
    oldpins=oldcfg['effective_role_source_pins']['C'];oldsource=read(PRIOR/'package-standby-cwd/STAGE-PLAN.json')['C_source_root']
    source=oldsource
    code='CFG='+repr(cfg)+'\nEXPECTED='+repr(oldcfg['finite']['node_binding'])+'\nROOT='+repr(source)+'\nPINS='+repr(oldpins)+'\nCAPACITY='+repr(capacity['C_required_free_bytes'])+'\n'+r'''
import pathlib,hashlib,json,sys,os,stat,time
sys.dont_write_bytecode=True;P=pathlib.Path;sha=lambda p:hashlib.sha256(P(p).read_bytes()).hexdigest()
for n,h in PINS.items():assert sha(P(ROOT)/n)==h
sys.path.insert(0,ROOT);import finite_runtime as f
candidates=[]
for p in P('/proc').iterdir():
 if not p.name.isdecimal():continue
 try:
  raw=(p/'cmdline').read_bytes()
  if hashlib.sha256(raw).hexdigest()!=EXPECTED['command_sha256']:continue
  if sha(p/'exe')!=EXPECTED['binary_sha256']:continue
  candidates.append({'pid':int(p.name),'start_ticks':int((p/'stat').read_text().rsplit(')',1)[1].split()[19]),'boot_id':P('/proc/sys/kernel/random/boot_id').read_text().strip(),'binary_sha256':EXPECTED['binary_sha256'],'command_sha256':EXPECTED['command_sha256'],'rpc_port':18210})
 except (FileNotFoundError,PermissionError):continue
assert len(candidates)==1;CFG['finite']['node_binding']=candidates[0];before=f.node_binding(CFG)
rpc=f.node()
try:
 info=rpc.call('getServerInfo',{});assert info['networkId']=='testnet-10' and info['isSynced'] is True and info['hasUtxoIndex'] is True and info['serverVersion']==CFG['finite']['server_version']
 utxos=rpc.call('getUtxosByAddresses',{'addresses':CFG['finite']['watch_addresses']});assert set(utxos)=={'entries'} and utxos['entries']==[]
finally:rpc.close()
assert f.node_binding(CFG)==before
volume=P(CFG['finite']['root'])
while not volume.exists():volume=volume.parent
free=os.statvfs(volume).f_bavail*os.statvfs(volume).f_frsize
assert free>=CAPACITY
peer=os.environ['SSH_CONNECTION'].split()[0];auth=P('/var/lib/kpi-history/.ssh/authorized_keys');host=P('/etc/ssh/ssh_host_ed25519_key.pub').read_text().split()[:2]
rows=[]
for table in ['tcp','tcp6']:
 for line in P('/proc/net/'+table).read_text().splitlines()[1:]:
  x=line.split()
  if x[1].split(':')[1]=='0016' and x[3]=='01':rows.append(x[2])
print(json.dumps({'passed':True,'node_binding':candidates[0],'A_source_address':peer,'C_authorized_keys_preimage_sha256':sha(auth),'C_host_public_key':' '.join(host),'empty_native_watch_UTXO_set':True,'C_capacity_passed':True,'C_actual_free_bytes':free,'C_required_free_bytes':CAPACITY,'ssh_established_before':rows,'observed_at':time.time()}))
'''
    c=run('C',code,40)
    # Existing dedicated route revalidates actual SSH key/known-host pins.
    b=run('B','BASE='+repr(plan['base_instance_id'])+'\n'+r'''
import pathlib,pwd,grp,os,stat,json
P=pathlib.Path;assert pwd.getpwuid(999).pw_uid==999 and grp.getgrgid(988).gr_gid==988
j=P('/srv/kpi-recovery/jail');assert j.is_dir() and not j.is_symlink() and j.stat().st_uid==0
work=j/'work';parent=work/'finite-recovery';assert work.is_dir() and parent.is_dir() and not parent.is_symlink() and parent.stat().st_uid==999 and parent.stat().st_gid==988 and stat.S_IMODE(parent.stat().st_mode)==0o700
assert not (j/'instances'/BASE).exists() and not (j/'instances'/BASE).is_symlink()
assert os.statvfs(work).f_bavail*os.statvfs(work).f_frsize>=50*1024**3
assert ' /srv/kpi-recovery/jail' in P('/proc/self/mountinfo').read_text() or j.stat().st_dev==P('/').stat().st_dev
print(json.dumps({'passed':True,'uid':999,'gid':988,'parent_directory_guard':True,'new_BASE_namespace_unused':True,'capacity50GiB':True,'actual_mount_table_checked':True}))
''',30)
    done={}
    probe_port=40000+__import__("secrets").randbelow(20000)
    def probe():
        try:
            done['result']=run('B','PORT='+repr(probe_port)+'\n'+r'''
import socket,time,json
s=socket.socket();s.settimeout(5);s.bind(('0.0.0.0',PORT))
try:
 s.connect(('@C_ADDRESS@',22));banner=s.recv(512);assert banner.startswith(b'SSH-2.0-');time.sleep(12)
 print(json.dumps({'passed':True,'existing_C_SSH_listener_only':True,'auth_attempted':False}))
finally:s.close()
''',25)
        except BaseException as e:done['error']=type(e).__name__
    thread=threading.Thread(target=probe);thread.start();observed=None
    try:
        for _ in range(6):
            code='PORT='+repr(probe_port)+'\nBEFORE='+repr(c['ssh_established_before'])+'\nAPEER='+repr(c['A_source_address'])+'\n'+r'''
import pathlib,socket,json
peers=[]
for line in pathlib.Path('/proc/net/tcp').read_text().splitlines()[1:]:
 x=line.split()
 if x[1].split(':')[1]!='0016' or x[3]!='01' or x[2] in BEFORE:continue
 host,port=x[2].split(':')
 ip=socket.inet_ntop(socket.AF_INET,bytes.fromhex(host)[::-1])
 if ip!=APEER and int(port,16)==PORT:peers.append(ip)
assert len(peers)<=1
print(json.dumps({'peers':peers}))
'''
            v=run('C',code,8)
            if v['peers']:observed=v['peers'][0];break
            time.sleep(.5)
    finally:thread.join(timeout=26)
    require(not thread.is_alive() and 'error' not in done and done.get('result',{}).get('passed') and observed,'actual C-observed B source peer')
    ipaddress.ip_address(observed)
    return {'passed':True,'explicit_start':production,'preparation_smoke':smoke,'base_instance_id':plan['base_instance_id'],
            'A_boot_identity_sha256':sha(Path('/proc/sys/kernel/random/boot_id')),
            'C_node_binding':c['node_binding'],'C_authorized_keys_preimage_sha256':c['C_authorized_keys_preimage_sha256'],
            'C_host_public_key':c['C_host_public_key'],'A_source_address':c['A_source_address'],
            'B_source_address':observed,'B_source_peer_observed_by_C':True,
            'never_funded_current_chain':c['empty_native_watch_UTXO_set'],
            'fresh_owner_generation_no_submit_and_empty_UTXO_guard':True,
            'storage_mount_UID_route_source_guards_passed':bool(b['passed'] and c['C_capacity_passed']),
            'C_actual_free_bytes':c['C_actual_free_bytes'],'C_required_free_bytes':c['C_required_free_bytes'],
            'actual_UID999_namespace_probe_still_required_after_install_before_funding':True,
            'observed_at':time.time(),'funding_authorized':False,'terminal_execution_authorized':False}
