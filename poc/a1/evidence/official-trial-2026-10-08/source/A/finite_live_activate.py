"""Future exact-authority activation of the predeclared finite live roles.
Not invoked by standby installer. No transaction submission in this helper.
External hashes bind manifests/config/checklist/authority before any mutation.
"""
import argparse,copy,hashlib,json,os,pathlib,socket,subprocess,time,stat
import finite_install as f
from fixed_terms import u64
P=pathlib.Path

def check_authority(cfg,authority,check,check_sha,manifest):
 f.require(authority['schema']=='kpi-finite-exact-user-live-authorization/v1' and authority['explicit_live_start_authorization'] is True,'later exact user live authority required')
 f.require(cfg['run_id']==authority['run_id']==check['run_id']==manifest['run_id'] and cfg['mode']=='finite-live-native' and cfg['execution_authorized'] is True and cfg['terminal_execution_authorized'] is True,'live run/authorization binding')
 f.require(authority['network']==check['network']==cfg['terminal_policy']['network']=='testnet-10' and authority['checklist_sha256']==check_sha==cfg['execution_checklist_sha256'],'exact testnet checklist')
 f.require(check['preparation_ready_for_live'] is True and check['manifest_sha256']==cfg['manifest_sha256'] and check['inventory_sha256']==cfg['inventory_sha256'],'exact reviewed package')
 f.require(cfg['worker_source_sha256']==check['worker_source_sha256'] and cfg['worker_files_sha256']==check['worker_files_sha256'],'genuine frozen worker identity')
 t=check['fixed_terms'];f.require(t['manifest_sha256']==cfg['manifest_sha256'] and u64(authority['max_wallet_debit_sompi'])==u64(t['maximum_wallet_debit_sompi']) and u64(authority['max_funding_fee_sompi'])==u64(t['funding_fee_cap_sompi']),'exact amount caps')
 f.require(all(type(authority[k]) is int and authority[k]==1 for k in ['funding_attempts','continuation_attempts','terminal_attempts']) and authority['terminal_exit_broadcast_authorized'] is True,'one attempt phases')
 p=cfg['terminal_policy'];f.require(p['run_id']==cfg['run_id'] and p['branch']=='s1_terminal' and p['max_attempts']==1 and p['execution_checklist_sha256']==check_sha and p['manifest_sha256']==cfg['manifest_sha256'] and p['inventory_sha256']==cfg['inventory_sha256'],'frozen terminal policy')
 f.require(u64(p['fee_sompi'])==u64(t['branch_fees_sompi']['s1_terminal']) and type(p['exact_payout']) is int and p['exact_payout']==u64(t['branch_recipient_payouts_sompi']['s1_terminal']),'exact terminal fee/payout')
 masked=copy.deepcopy(cfg)
 for k in ['execution_authorized','terminal_execution_authorized','funding_authorized','poweroff_authorized']:masked[k]=False
 f.validate(manifest,masked,manifest['config_sha256']);return masked

def stop_new_standby(m):
 # The run and exact systemd fragment hash are supplied by the inspected runtime
 # binding. Only our separate new standby units can ever be stopped here.
 f.require(set(m['new_standby_units'])=={m['role']},'only role-local standby unit')
 for role,item in m['new_standby_units'].items():
  expected='kpi-finite-'+role.lower()+'-'+m['standby_run_id']+'.service';f.require(item['unit']==expected,'only new standby unit may stop')
  target=P('/etc/systemd/system')/expected;f.file(str(target),item['unit_sha256'])
  subprocess.run(['systemctl','stop',expected],check=True,capture_output=True,timeout=200)
  v=dict(x.split('=',1) for x in subprocess.check_output(['systemctl','show',expected,'--property=ActiveState,MainPID,ControlPID'],text=True,timeout=5).splitlines());f.require(v['ActiveState'] in ['inactive','failed'] and v['MainPID']==v['ControlPID']=='0','new standby not fully stopped')

def routes(m):
 path=P(f.path(m['authorized_keys_path']));f.require(str(path)=='/var/lib/kpi-history/.ssh/authorized_keys','dedicated forced SSH account only');old=f.file(str(path),m['authorized_keys_preimage_sha256'],owner=m['authorized_keys_uid']);rows=old.decode().splitlines();receipt=[]
 f.require({x['role'] for x in m['route_keys']}=={'B','controller'},'two fixed role credentials')
 for item in m['route_keys']:
  role=item['role'];key_parts=item['public_key'].split();f.require(len(key_parts)>=2,'public key framing');public=' '.join(key_parts[:2]);f.require(__import__('re').fullmatch(r'ssh-ed25519 [A-Za-z0-9+/]+={0,2}',public) is not None,'fixed ed25519 public credential')
  command='/usr/bin/python3 '+m['source_root']+'/gateway.py --role='+role+' --config '+m['config']+' --config-sha256 '+m['config_sha256']+' --bound-run '+m['run_id']+' --control-socket '+m['socket_root']+'/control.sock'
  indexes=[i for i,row in enumerate(rows) if hashlib.sha256(row.encode()).hexdigest()==item['standby_line_sha256']];f.require(len(indexes)==1 and public in rows[indexes[0]],'new standby credential lineage')
  prefix=rows[indexes[0]].split(' '+public,1)[0];f.require(prefix.count('command="')==1 and __import__('re').search(r'(?:^|,)from="[^"]+"',prefix) is not None,'inspected source restriction required');prefix,count=__import__('re').subn(r'command="[^"]*"','command="'+command+'"',prefix);f.require(count==1,'exact existing forced command replacement');replacement=prefix+' '+public+' kpi-finite-'+m['run_id']+'-'+role
  rows[indexes[0]]=replacement;receipt.append({'role':role,'forced_command_sha256':hashlib.sha256(command.encode()).hexdigest(),'line_sha256':hashlib.sha256(replacement.encode()).hexdigest()})
 metadata=path.stat();raw=('\n'.join(rows)+'\n').encode();tmp=path.parent/('authorized_keys.'+m['run_id']+'.pending');fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as stream:os.fchown(stream.fileno(),metadata.st_uid,metadata.st_gid);os.fchmod(stream.fileno(),metadata.st_mode&0o777);stream.write(raw);stream.flush();os.fsync(stream.fileno())
 f.require(hashlib.sha256(path.read_bytes()).hexdigest()==m['authorized_keys_preimage_sha256'],'forced-key preimage changed');os.replace(tmp,path);fd=os.open(path.parent,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 return {'authorized_keys_sha256':hashlib.sha256(raw).hexdigest(),'routes':receipt}

def write_unit(m,cfg,masked):
 raw=f.render(m,masked).encode();target=P('/etc/systemd/system')/m['unit'];fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
 with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
 fd=os.open(target.parent,os.O_DIRECTORY);os.fsync(fd);os.close(fd);return hashlib.sha256(raw).hexdigest()

def provision_B_recovery_parent(cfg):
 # Provision only the fixed output parent; recover_exit owns its exclusive child.
 f.require(f.RUN.fullmatch(cfg['run_id']) is not None and cfg['B_recovery_output']=='/work/finite-recovery/'+cfg['run_id'],'exact B recovery output')
 import stat
 fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:
  for name,owner in [('srv',0),('kpi-recovery',0),('jail',0),('work',999)]:
   nxt=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=nxt;s=os.fstat(fd)
   f.require(s.st_uid==owner and not s.st_mode&0o022,'owned real B output ancestry')
  try:os.mkdir('finite-recovery',mode=0o700,dir_fd=fd);created=True
  except FileExistsError:created=False
  parent=os.open('finite-recovery',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
  try:
   if created:os.fchown(parent,999,988);os.fchmod(parent,0o700);os.fsync(parent);os.fsync(fd)
   s=os.fstat(parent);f.require(s.st_uid==999 and s.st_gid==988 and stat.S_IMODE(s.st_mode)==0o700,'private B output parent')
   try:os.stat(cfg['run_id'],dir_fd=parent,follow_symlinks=False)
   except FileNotFoundError:pass
   else:raise ValueError('refuse reused B recovery output including symlink')
  finally:os.close(parent)
 finally:os.close(fd)
 return {'recovery_parent':'/work/finite-recovery','uid':999,'gid':988,'mode':'0700','created':created,'run_child_absent':True}

def qualify_B_recovery_storage(unit):
 # Enter the settled service mount/root/net namespaces with its exact identity.
 import uuid
 pid=subprocess.check_output(['systemctl','show',unit,'--property=MainPID','--value'],text=True,timeout=5).strip()
 f.require(pid.isdecimal() and int(pid)>0,'actual B namespace PID required')
 proc=P('/proc')/pid;start_ticks=(proc/'stat').read_text().rsplit(')',1)[1].split()[19];mnt=os.readlink(proc/'ns/mnt')
 child='.qualification-'+uuid.uuid4().hex
 code="""import os,pathlib,json,stat,tempfile
assert os.getuid()==999 and os.getgid()==988
p=pathlib.Path('/work/finite-recovery');s=p.lstat();assert stat.S_ISDIR(s.st_mode) and s.st_uid==999 and s.st_gid==988 and stat.S_IMODE(s.st_mode)==0o700
child=p/CHILD;assert not os.path.lexists(child);child.mkdir(mode=0o700)
try:
 fd=os.open(child/'write-check',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as stream:stream.write(b'bounded B storage check');stream.flush();os.fsync(stream.fileno())
 assert (child/'write-check').read_bytes()==b'bounded B storage check'
 fd=os.open(child,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 try:child.mkdir(mode=0o700)
 except FileExistsError:pass
 else:raise AssertionError('reused child accepted')
 for n in ['/usr/bin/python3','/usr/bin/node','/usr/bin/ssh','/software/kpi-poc-a1','/software/a1_reference']:assert os.access(n,os.X_OK)
 with tempfile.TemporaryFile() as temp:temp.write(b'tmp-check');temp.flush();os.fsync(temp.fileno())
finally:
 (child/'write-check').unlink();child.rmdir();fd=os.open(p,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
assert not os.path.lexists(child)
print(json.dumps({'storage_ready':True,'uid':999,'gid':988,'exclusive_create_write_read_fsync':True,'reuse_rejected':True,'own_probe_removed':True,'executables_present':True,'private_tmp_writable':True}))
""".replace('CHILD',repr(child))
 v=subprocess.run(['/usr/bin/nsenter','--target',pid,'--mount','--net','--root=/proc/'+pid+'/root','--wd=/proc/'+pid+'/root/work','--setgid=988','--setuid=999','/usr/bin/python3','-B','-c',code],capture_output=True,text=True,timeout=20)
 f.require(v.returncode==0,'actual B recovery storage qualification failed')
 receipt=json.loads(v.stdout);f.require(receipt.get('storage_ready') is True,'actual B recovery storage receipt')
 f.require((proc/'stat').read_text().rsplit(')',1)[1].split()[19]==start_ticks and os.readlink(proc/'ns/mnt')==mnt and subprocess.check_output(['systemctl','show',unit,'--property=MainPID','--value'],text=True,timeout=5).strip()==pid,'B process changed during storage check')
 return dict(receipt,pid=int(pid),start_ticks=start_ticks,mount_namespace=mnt)

def qualify_B_loopback_ack(unit,run,config_sha256):
 pid=subprocess.check_output(['systemctl','show',unit,'--property=MainPID','--value'],text=True,timeout=5).strip();f.require(pid.isdecimal() and int(pid)>0,'actual B loopback process required')
 proc=P('/proc')/pid;start=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19];boot=P('/proc/sys/kernel/random/boot_id').read_text().strip();group=proc.joinpath('cgroup').read_text().strip()
 path=P('/srv/kpi-recovery/jail/work/final-qualification/autonomous-results')/run/'B-LOOPBACK-READY.json';fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 with os.fdopen(fd,'rb') as stream:
  st=os.fstat(stream.fileno());f.require(stat.S_ISREG(st.st_mode) and st.st_uid==999 and st.st_gid==988 and st.st_nlink==1 and stat.S_IMODE(st.st_mode)==0o600 and st.st_size<=4096,'private B loopback acknowledgement file');receipt=json.loads(stream.read(4097))
 f.require(receipt['run_id']==run and receipt['PID']==int(pid) and receipt['boot']==boot and receipt['start_ticks']==start and receipt['config_sha256']==config_sha256 and receipt['inside_service_cgroup']==group and unit in group and receipt['IPv4_loopback_bind_connect_send_ack'] is True and receipt['no_external_RPC'] is True,'actual same-cgroup B loopback acknowledgement binding')
 f.require(proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==start and subprocess.check_output(['systemctl','show',unit,'--property=MainPID','--value'],text=True,timeout=5).strip()==pid,'B process changed during loopback acknowledgement check')
 return {'loopback_ready':True,'pid':int(pid),'start_ticks':start,'actual_controller_service_cgroup':True}

def activate(m,cfg,masked):
 f.require(os.geteuid()==0,'root administrator required')
 for n,h in m['source_pins'].items():f.file(m['source_root']+'/'+n,h)
 f.require(not (P('/etc/systemd/system')/m['unit']).exists(),'live namespace already installed')
 state=P(m['state_root']);f.require(state.is_dir() and not state.is_symlink() and state.stat().st_uid==0,'precreated root live state')
 if m['role']=='C':f.validate_prefund(m,cfg)
 else:provision_B_recovery_parent(cfg)
 claim=state/('live-activation-claimed-'+m['role']+'.json');fd=os.open(claim,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as stream:stream.write(f.encode({'run_id':m['run_id'],'config_sha256':m['config_sha256'],'at':time.time(),'retry_allowed':False}));stream.flush();os.fsync(stream.fileno())
 stop_new_standby(m);created=[]
 try:
  if m['role']=='C':P(m['socket_root']).mkdir(mode=0o750,exist_ok=False);os.chown(m['socket_root'],0,m['gateway_gid']);os.chmod(m['socket_root'],0o750)
  else:
   out=P('/srv/kpi-recovery/jail/work/final-qualification/autonomous-results')/cfg['run_id'];f.require(not out.exists(),'new B output namespace required');out.mkdir(mode=0o700);os.chown(out,999,988);f.require(cfg['B_locator_path']=='/work/final-qualification/autonomous-results/'+cfg['run_id']+'/old-S0-locator.json' and cfg['B_checkpoint_path']=='/work/final-qualification/autonomous-results/'+cfg['run_id']+'/pre-funding-checkpoint.json','exact B starting input paths')
   for name,value in [('old-S0-locator.json',cfg['locator']),('pre-funding-checkpoint.json',cfg['checkpoint'])]:
    fd=os.open(out/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:os.fchown(stream.fileno(),999,988);stream.write(f.encode(value));stream.flush();os.fsync(stream.fileno())
   directory=os.open(out,os.O_DIRECTORY);os.fsync(directory);os.close(directory)
   for n in ['access.json','id_ed25519','known_hosts']:f.file(m['credentials']+'/'+n,m['credential_pins'][n],owner=999 if n=='id_ed25519' else 0,private=n=='id_ed25519')
  unit_sha=write_unit(m,cfg,masked);created.append(m['unit']);subprocess.run(['systemctl','daemon-reload'],check=True,capture_output=True,timeout=20);subprocess.run(['systemctl','start',m['unit']],check=True,capture_output=True,timeout=30)
  if m['role']=='C':
   deadline=time.monotonic()+45
   while not P(m['socket_root']+'/control.sock').exists():
    f.require(time.monotonic()<deadline,'live controller socket deadline');time.sleep(.1)
   os.chown(m['socket_root']+'/control.sock',0,m['gateway_gid']);f.control(m,'finite-checkpoint')
   # Only kernel-root admin role can prepare; B/controller SSH never gain it.
   with socket.socket(socket.AF_UNIX) as s:
    s.settimeout(25);s.connect(m['socket_root']+'/control.sock');s.sendall(f.encode({'run_id':cfg['run_id'],'op':'prepare','authenticated_role':'admin'})+b'\n');v=json.loads(s.makefile('rb').readline(262145))
   f.require(v.get('prepared') is True and v['S1_pointer_supplied'] is False,'original finite admin preparation')
   collector='kpi-finite-collector-'+cfg['run_id']+'.service';text='[Unit]\nDescription=Finite fixed-run pre-funding collector\n[Service]\nType=simple\nUser=root\nRestart=no\nNoNewPrivileges=yes\nProtectSystem=strict\nPrivateTmp=yes\nMemoryAccounting=yes\nCPUAccounting=yes\nMemoryHigh=3G\nMemoryMax=4G\nCPUQuota=250%\nTasksMax=64\nKillMode=control-group\nTimeoutStopSec=180\nReadWritePaths='+cfg['finite']['root']+'\nExecStart=/usr/bin/python3 '+m['source_root']+'/finite_capture.py --config '+m['config']+' continuation\n'
   target=P('/etc/systemd/system')/collector;fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
   with os.fdopen(fd,'w') as stream:stream.write(text);stream.flush();os.fsync(stream.fileno())
   created.append(collector);subprocess.run(['systemctl','daemon-reload'],check=True,capture_output=True,timeout=20);subprocess.run(['systemctl','start',collector],check=True,capture_output=True,timeout=30)
   deadline=time.monotonic()+90
   while True:
    f.require(time.monotonic()<deadline,'collector before-funding deadline')
    try:f.control(m,'funding-ready');break
    except (ValueError,OSError):time.sleep(.1)
   route=routes(m);return {'run_id':cfg['run_id'],'prepared':True,'collector_started_before_funding':True,'S1_pointer_supplied':False,'unit':m['unit'],'unit_sha256':unit_sha,'collector_unit':collector,'routes':route,'at':time.time()}
  # B live controller is waiting for genuine C acceptance; never manually ARM.
  status=subprocess.check_output(['systemctl','show',m['unit'],'--property=ActiveState','--value'],text=True,timeout=5).strip();f.require(status=='active','B live service failed');out=P('/srv/kpi-recovery/jail/work/final-qualification/autonomous-results')/cfg['run_id'];deadline=time.monotonic()+45
  while not (out/'controller.json').exists():f.require(time.monotonic()<deadline,'B startup event deadline');time.sleep(.1)
  f.require(not any((out/n).exists() for n in ['boundary-error.json','C-delivery-failed.json','result.json','arm-attempt.json']),'B live startup rejected')
  loopback=qualify_B_loopback_ack(m['unit'],cfg['run_id'],m['config_sha256'])
  storage=qualify_B_recovery_storage(m['unit'])
  return {'loopback_ready':True,'loopback_qualification':loopback,'recovery_storage_ready':True,'recovery_storage_qualification':storage,'run_id':cfg['run_id'],'B_started_before_funding':True,'unarmed':True,'unit':m['unit'],'unit_sha256':unit_sha,'at':time.time()}
 except BaseException:
  for unit in reversed(created):subprocess.run(['systemctl','stop',unit],capture_output=True,timeout=200)
  raise
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in ['manifest','manifest-sha256','config','config-sha256','authority','authority-sha256','checklist','checklist-sha256']:p.add_argument('--'+name,required=True)
 a=p.parse_args();m=json.loads(f.file(a.manifest,a.manifest_sha256));cfg=json.loads(f.file(a.config,a.config_sha256));authority=json.loads(f.file(a.authority,a.authority_sha256));check=json.loads(f.file(a.checklist,a.checklist_sha256));f.require(m['config']==a.config and m['config_sha256']==a.config_sha256,'exact installed live config');masked=check_authority(cfg,authority,check,a.checklist_sha256,m);print(json.dumps(activate(m,cfg,masked),sort_keys=True))
