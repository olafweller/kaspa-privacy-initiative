"""Exact isolated standby installation. All execution flags must remain false.
No funding, prepare, ARM, forwarding, global config replacement or old-unit stop.
Manifest and config hashes are independently supplied by the reviewed executor.
"""
import argparse,hashlib,json,os,pathlib,re,socket,stat,subprocess,sys,time
P=pathlib.Path
RUN=re.compile(r'[a-z0-9][a-z0-9-]{7,119}\Z')
def require(x,m):
 if not x:raise ValueError(m)
def sha(p):return hashlib.sha256(P(p).read_bytes()).hexdigest()
def encode(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def path(x):
 require(type(x) is str and x.startswith('/') and re.fullmatch(r'[a-zA-Z0-9_./-]+',x) and '..' not in P(x).parts,'unsafe installed path');return x
def unix_path(x):
 require(type(x) is str and 0<len(x.encode('utf-8'))<=107 and '\0' not in x,'AF_UNIX pathname exceeds 107 UTF-8 bytes');return x
def file(p,h,owner=0,private=False):
 p=P(path(p));fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 with os.fdopen(fd,'rb') as f:
  s=os.fstat(f.fileno());require(stat.S_ISREG(s.st_mode) and s.st_uid==owner and s.st_nlink==1 and not s.st_mode&0o022,'owned immutable installed file');require(not private or stat.S_IMODE(s.st_mode)==0o600,'private key mode');raw=f.read()
 require(hashlib.sha256(raw).hexdigest()==h,'installed file hash');return raw
def validate(m,cfg,pin):
 require(m['schema']=='kpi-finite-isolated-standby-install/v1' and m['role'] in ['B','C'] and RUN.fullmatch(m['run_id']),'install identity')
 require(cfg['run_id']==m['run_id'] and cfg['mode']=='finite-live-native' and all(cfg.get(k) is False for k in ['execution_authorized','terminal_execution_authorized','funding_authorized','poweroff_authorized']),'standby authority only')
 require(m['config_sha256']==pin and m['unit']=='kpi-finite-'+m['role'].lower()+'-'+m['run_id']+'.service','unit/config binding')
 for k in ['config','source_root','state_root']:path(m[k])
 require(P(m['config']).parent==P(m['state_root']) and P(m['source_root'])!=P('/opt/kpi-g5-capture'),'isolated config/source roots')
 require(m['source_pins']==cfg['effective_role_source_pins'][m['role']],'configuration/installed source manifest')
 require(m['source_pins'] and all(re.fullmatch(r'[a-zA-Z0-9_-]+\.(py|mjs|json)',n) and re.fullmatch('[a-f0-9]{64}',h) for n,h in m['source_pins'].items()),'strict source manifest')
 if m['role']=='C':
  require(cfg['controller_uid']==0 and cfg['finite']['root']==m['state_root']+'/finite-runs','root observer/run directory binding')
  require(m['gateway_uid']==cfg['gateway_uid'] and type(m['gateway_gid']) is int and m['gateway_gid']>=0,'gateway account binding');path(m['socket_root']);unix_path(m['socket_root']+'/control.sock')
  require(m['socket_root']==m['state_root']+'/socket' and cfg['finite']['role_sources']=={n:{'path':m['source_root']+'/'+n,'sha256':h} for n,h in m['source_pins'].items()},'exact C source/socket binding')
 else:
  for k in ['jail','credentials']:path(m[k])
  require(m['jail']=='/srv/kpi-recovery/jail' and m['uid']==999 and m['gid']==988,'original B isolation binding')
 return cfg

def render(m,cfg):
 validate(m,cfg,m['config_sha256']);r=m['run_id'];lines=['[Unit]','Description=Isolated unfunded finite '+m['role']+' '+r,'[Service]','Type=simple','Restart=no','TimeoutStopSec=180','KillMode=control-group','Nice=10','MemoryAccounting=yes','CPUAccounting=yes','MemoryHigh=3G','MemoryMax=4G','CPUQuota=250%','TasksMax=64','LimitCORE=0','NoNewPrivileges=yes','ProtectSystem=strict','PrivateTmp=yes','PrivateDevices=yes','ProtectHome=yes','Environment=PYTHONNOUSERSITE=1','Environment=PYTHONDONTWRITEBYTECODE=1','UMask=0077']
 if m['role']=='C':
  lines+=['User=root','Group=root','BindReadOnlyPaths='+m['config']+':/etc/kpi-g5-independent.json','BindPaths='+m['socket_root']+':/run/kpi-g5-independent','ReadWritePaths='+m['state_root']+'/finite-runs '+m['socket_root'],'ExecStart=/usr/bin/python3 '+m['source_root']+'/independent_controller.py']
 else:
  lines+=['User=999','Group=988','RootDirectory='+m['jail'],'MountAPIVFS=yes','CapabilityBoundingSet=','RestrictAddressFamilies=AF_UNIX AF_INET','IPAddressDeny=any','IPAddressAllow=@C_ADDRESS@','IPAddressAllow=127.0.0.1/32','BindReadOnlyPaths=/usr /lib /lib64 /bin','BindReadOnlyPaths='+m['credentials']+':/credentials','BindReadOnlyPaths='+m['config']+':/lifecycle/'+r+'/config.json','BindReadOnlyPaths='+m['config']+':/software/independent-config.json','ReadWritePaths=+/work +/backup-fixture','Environment=KPI_LIFECYCLE_RUN_ID='+r,'Environment=KPI_LIFECYCLE_CONFIG_SHA256='+m['config_sha256'],'Environment=KPI_RUN_CONFIG=/lifecycle/'+r+'/config.json','Environment=RAYON_NUM_THREADS=2','Environment=PYTHONPATH=/software','WorkingDirectory=/work','ExecStartPre=/usr/bin/python3 /software/lifecycle_entry.py start '+r,'ExecStopPost=/usr/bin/python3 /software/lifecycle_entry.py stop '+r,'ExecStart=/usr/bin/python3 /software/B_controller_run.py --bound-run '+r]
  lines+=['BindReadOnlyPaths='+m['source_root']+'/'+n+':/software/'+n for n in sorted(m['source_pins'])]
 return '\n'.join(lines)+'\n'

def control(m,op):
 with socket.socket(socket.AF_UNIX) as s:
  s.settimeout(20);s.connect(m['socket_root']+'/control.sock');s.sendall(encode({'op':op,'run_id':m['run_id'],'authenticated_role':'controller'})+b'\n');raw=s.makefile('rb').readline(262145)
 require(len(raw)<=262144 and raw.endswith(b'\n'),'bounded controller reply');v=json.loads(raw);require('error' not in v,'finite controller rejected '+op);return v

def validate_prefund(m,cfg):
 run=P(cfg['finite']['root'])/m['run_id'];require(run.is_dir() and not run.is_symlink(),'precreated pinned prefunding run required')
 pref=json.loads(file(str(run/'PREFUND.json'),m['prefund_sha256']));seal=json.loads(file(str(run/'PREFUND-SEAL.json'),m['prefund_seal_sha256']))
 require(not any((run/n).exists() for n in ['observer-prefunding','observer-pre-funding','events.jsonl','FAULT.json','B-result.json','S1-SEAL.json']),'fresh prefix never observed/faulted')
 digest=lambda v:hashlib.sha256(encode(v)).hexdigest()
 require(pref['run_id']==m['run_id'] and seal['run_id']==m['run_id'] and pref['checkpoint']==cfg['checkpoint'],'exact fresh prefund binding')
 require(seal['schema']=='kpi-C-native-validated-prefix-seal/v1' and seal['phase']=='pre-funding' and seal['network']=='testnet-10','prefund seal contract')
 require(seal['config_sha256']==digest({k:v for k,v in cfg.items() if k not in {'checkpoint','locator'}}) and seal['role_sources_sha256']==digest(cfg['finite']['role_sources']) and seal['checkpoint_sha256']==digest(cfg['checkpoint']),'prefund seal/config/source/checkpoint hashes')
 for field in ['genesis','server_version']:require(seal[field]==cfg['finite'][field],'prefund '+field)
 for field in ['native','sdk']:require(seal[field+'_sha256']==cfg['finite'][field]['sha256'],'prefund tool pin')
 return pref,seal

def qualification_probe(pid,probe,state):
 require(type(pid) is str and pid.isdecimal() and int(pid)>0,'actual live B PID')
 v=subprocess.run(['/usr/bin/nsenter','--target',pid,'--mount','--net','--root=/proc/'+pid+'/root','--wd=/proc/'+pid+'/root/work','--setgid=988','--setuid=999','/usr/bin/python3','-c',probe],capture_output=True,timeout=20)
 for name,raw in [('B-status-probe.stdout',v.stdout),('B-status-probe.stderr',v.stderr)]:
  fd=os.open(P(state)/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
 fd=os.open(state,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 require(v.returncode==0,'actual B status probe rejected; private output retained')
 return v

def apply(m,cfg):
 validate(m,cfg,m['config_sha256'])
 require(os.geteuid()==0,'root executor required');state=P(m['state_root']);require(state.is_dir() and not state.is_symlink() and state.stat().st_uid==0 and not state.stat().st_mode&0o022,'isolated root-owned state')
 for n,h in m['source_pins'].items():file(m['source_root']+'/'+n,h)
 target=P('/etc/systemd/system')/m['unit'];require(not target.exists() and not target.is_symlink(),'unit namespace already used')
 if m['role']=='C':
  # The fixed existing proxy port cannot overlap another observer.
  with socket.socket() as s:s.bind(('127.0.0.1',19410))
  validate_prefund(m,cfg)
  sys.path.insert(0,m['source_root']);from finite_runtime import settings,node_binding
  require(P(sys.modules['finite_runtime'].__file__).resolve().parent==P(m['source_root']).resolve(),'installed runtime origin');settings(cfg);node_binding(cfg)
  P(m['socket_root']).mkdir(mode=0o750,exist_ok=False);os.chown(m['socket_root'],0,m['gateway_gid']);os.chmod(m['socket_root'],0o750)
 else:
  for n in ['access.json','id_ed25519','known_hosts']:file(m['credentials']+'/'+n,m['credential_pins'][n],owner=999 if n=='id_ed25519' else 0,private=n=='id_ed25519')
 raw=render(m,cfg).encode();fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
 with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 fd=os.open(target.parent,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 try:
  subprocess.run(['systemctl','daemon-reload'],check=True,capture_output=True,timeout=20);subprocess.run(['systemctl','start',m['unit']],check=True,capture_output=True,timeout=30)
  deadline=time.monotonic()+45;cp=None
  while time.monotonic()<deadline:
   props=dict(x.split('=',1) for x in subprocess.check_output(['systemctl','show',m['unit'],'--property=ActiveState,SubState,MainPID,NRestarts'],text=True,timeout=5).splitlines())
   require(props['ActiveState'] not in ['failed','inactive'],'new standby failed')
   if props['ActiveState']=='active' and props['SubState']=='running' and props['NRestarts']=='0':
    if m['role']=='B':
     # Type=simple may report running before RootDirectory/binds/exec settle.
     # Open the target working-directory FD from the host before nsenter.
     actual=P('/proc')/props['MainPID']/'root'
     if props['MainPID']=='0' or not (actual/'work').is_dir() or not (actual/'software/B_controller_run.py').is_file() or not (actual/'lifecycle'/m['run_id']/'config.json').is_file():
      time.sleep(.1);continue
     # Actual B credential/source/mount namespace and successful C status, not PID alone.
     probe="import sys,json;sys.path.insert(0,'/software');from access_check import query;s=query({'action':'independent','op':'status','run_id':"+repr(m['run_id'])+"});assert s['run_id']=="+repr(m['run_id'])+" and not s['events'] and not s['faulted'] and s['terminal_result'] is None;print(json.dumps(s))"
     qualification_probe(props['MainPID'],probe,state)
     time.sleep(3);out=P('/proc')/props['MainPID']/'root/work/final-qualification/autonomous-results'/m['run_id'];require((out/'controller.json').exists() and not any((out/n).exists() for n in ['boundary-error.json','C-delivery-failed.json','result.json','arm-attempt.json']),'actual B standby errored or armed');break
    if P(m['socket_root']+'/control.sock').exists():
     os.chown(m['socket_root']+'/control.sock',0,m['gateway_gid']);cp=control(m,'finite-checkpoint');status=control(m,'status');require(not status['events'] and not status['faulted'] and status['terminal_result'] is None,'C not empty/unarmed');probe=status['latest_probe'];require(probe and probe['all_reachable'] and not probe['uncertain'] and -2<=time.time()-probe['at']<=5,'actual independently baselined A routes unavailable');break
   time.sleep(.2)
  else:raise TimeoutError('new standby actual startup deadline')
  return {'schema':'kpi-finite-isolated-standby-install-receipt/v1','role':m['role'],'run_id':m['run_id'],'unit':m['unit'],'config_sha256':m['config_sha256'],'unit_sha256':hashlib.sha256(raw).hexdigest(),'active':True,'finite_checkpoint':cp,'execution_authorized':False,'terminal_execution_authorized':False,'old_units_stopped':False,'funding':False,'submit':False,'at':time.time()}
 except BaseException as exc:
  # This exclusive unit was created by this invocation. Never stop/adopt an old unit.
  failure={'schema':'kpi-finite-isolated-install-failure/v1','run_id':m['run_id'],'unit':m['unit'],'exception_type':type(exc).__name__,'new_unit_stop_exit_code':None,'old_units_stopped':False,'retry_allowed':False,'files_retained':True,'at':time.time()}
  target=state/'install-failure.json';fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as f:f.write(encode(failure));f.flush();os.fsync(f.fileno())
  fd=os.open(state,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
  # Durable failure precedes the bounded cleanup, including stop timeout.
  stopped=subprocess.run(['systemctl','stop',m['unit']],capture_output=True,timeout=200)
  fd=os.open(state/'new-unit-stop-receipt.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as f:f.write(encode({'unit':m['unit'],'exit_code':stopped.returncode,'old_units_stopped':False,'at':time.time()}));f.flush();os.fsync(f.fileno())
  raise


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--manifest-sha256',required=True);p.add_argument('--config',required=True);p.add_argument('--config-sha256',required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
 m=json.loads(file(a.manifest,a.manifest_sha256));cfg=json.loads(file(a.config,a.config_sha256));require(m['config']==a.config,'manifest config path');validate(m,cfg,a.config_sha256)
 print(json.dumps(apply(m,cfg)) if a.apply else render(m,cfg))
