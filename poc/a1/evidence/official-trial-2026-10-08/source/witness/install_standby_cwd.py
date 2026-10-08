"""Exact reviewed fresh false-authority C/B standby; no funding/prepare/ARM/submit."""
from pathlib import Path
import sys,json,hashlib,base64,subprocess,os
W=Path(__file__).resolve().parent;T=W.parent;P=T/'package-standby-cwd';Q=Path('@KPI_REPO@/.local/g5-preparation/orchestrator-dedicated-B-fresh-preparation-20261007T045400Z');sys.path.insert(0,str(Q));import dedicated_remote,remote_safety
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();enc=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def remote(role,code,timeout=120):return json.loads(dedicated_remote.run('@C_SSH_HOST@' if role=='C' else '@B_SSH_HOST@',remote_safety.wrap(code,role,'standby-install'),timeout))
def save(name,v):
 p=W/(name+'.private.json')
 with p.open('xb') as f:os.fchmod(f.fileno(),0o600);f.write(enc(v));f.flush();os.fsync(f.fileno())
def execute():
 release=json.loads((W/'ROOT-STANDBY-CWD-RELEASE.json').read_bytes());assert release['install_source_sha256']==sha(__file__) and release['plan_sha256']==sha(P/'STAGE-PLAN.json');binding=json.loads((W/'STANDBY-CWD-INSTALL-BINDING.private.json').read_bytes());plan=json.loads((P/'STAGE-PLAN.json').read_bytes());keys=json.loads((W/'STANDBY-CWD-ROUTE-KEYS.private.json').read_bytes());checked=json.loads((W/'B-credit-BASE-check-actual.private.json').read_bytes());assert checked['passed'] and checked['helper']['base_instance_id']==plan['base_instance_id']
 # Fresh immutable config/manifest/access staging precedes authorization lines.
 for role in ['B']:
  files={'state/install-manifest.json':(P/role/'install-manifest.json').read_bytes()}
  if role=='B':files.update({'state/config.json':(P/'B/config.json').read_bytes()})
  payload={n:base64.b64encode(v).decode() for n,v in files.items()};pins={n:hashlib.sha256(v).hexdigest() for n,v in files.items()};root=plan[role+'_root'];code='ROOT='+repr(root)+'\nROLE='+repr(role)+'\nFILES='+repr(payload)+'\nPINS='+repr(pins)+'\nCREDENTIALS='+repr(plan['B_credential_root'])+'\nBKEY='+repr(keys['B_credential_pins']['id_ed25519'])+'\n'+r'''
import pathlib,os,base64,hashlib,json
r=pathlib.Path(ROOT)
for n,text in FILES.items():
 raw=base64.b64decode(text,validate=True);assert hashlib.sha256(raw).hexdigest()==PINS[n]
 with (r/n).open('xb') as f:os.fchown(f.fileno(),0,986 if ROLE=='C' else 988);os.fchmod(f.fileno(),0o600 if n.endswith('install-manifest.json') else 0o440);f.write(raw);f.flush();os.fsync(f.fileno())
if ROLE=='B':
 d=pathlib.Path(CREDENTIALS);assert hashlib.sha256((d/'id_ed25519').read_bytes()).hexdigest()==BKEY;assert (d/'id_ed25519').stat().st_uid==999 and (d/'id_ed25519').stat().st_mode&0o777==0o600;os.chown(d,0,988);d.chmod(0o750)
print(json.dumps({'role':ROLE,'immutable_files_staged':len(FILES),'credential_directory_uid999_traversable_after_bind':ROLE=='B'}))
''';save(role+'-standby-cwd-install-input-stage',remote(role,code,30))
 Croot=plan['C_root'];lines=keys['lines'];added=False;Cstarted=False;Bstarted=False
 try:
  added=True;code='ROOT='+repr(Croot)+'\nPRE='+repr(keys['C_authorized_keys_preimage_sha256'])+'\nLINES='+repr(lines)+'\n'+r'''
import pathlib,json,hashlib,os
r=pathlib.Path(ROOT);a=pathlib.Path('/var/lib/kpi-history/.ssh/authorized_keys');before=a.read_bytes();assert hashlib.sha256(before).hexdigest()==PRE and (not before or before.endswith(b'\n'))
with (r/'state/authorized-keys.preimage').open('xb') as f:os.fchmod(f.fileno(),0o600);f.write(before);f.flush();os.fsync(f.fileno())
for line in LINES.values():assert line.encode() not in before and line.startswith('restrict,from=') and '\n' not in line[:-1]
with a.open('ab') as f:f.write(''.join(LINES.values()).encode());f.flush();os.fsync(f.fileno())
print(json.dumps({'exact_new_forced_lines_installed':2,'authorized_keys_sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'old_lines_preserved':a.read_bytes().startswith(before)}))
''';auth=remote('C',code,25);save('C-standby-cwd-forced-routes-installed',auth)
  results={}
  for role in ['C','B']:
   root=plan[role+'_root'];manifest=json.loads((P/role/'install-manifest.json').read_bytes());args=['/usr/bin/python3','-I',root+'/finite_install.py','--manifest',root+'/state/install-manifest.json','--manifest-sha256',sha(P/role/'install-manifest.json'),'--config',root+'/state/config.json','--config-sha256',manifest['config_sha256'],'--apply'];code='ROOT='+repr(root)+'\nARGS='+repr(args)+'\nINSTALLER_SHA='+repr(sha(P/role/'finite_install.py'))+'\n'+r'''
import pathlib,json,subprocess,os,hashlib,time,stat
r=pathlib.Path(ROOT);installer=r/'finite_install.py';fd=os.open(installer,os.O_RDONLY|os.O_NOFOLLOW)
with os.fdopen(fd,'rb') as stream:
 st=os.fstat(stream.fileno());assert st.st_uid==0 and st.st_nlink==1 and stat.S_ISREG(st.st_mode) and not st.st_mode&0o022;assert hashlib.sha256(stream.read()).hexdigest()==INSTALLER_SHA
began=time.monotonic();p=subprocess.run(ARGS,capture_output=True,timeout=285)
for n,raw in [('install.stdout',p.stdout),('install.stderr',p.stderr)]:
 with (r/'state'/n).open('xb') as f:os.fchmod(f.fileno(),0o600);f.write(raw);f.flush();os.fsync(f.fileno())
v={'passed':p.returncode==0,'returncode':p.returncode,'seconds':time.monotonic()-began,'stdout_sha256':hashlib.sha256(p.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(p.stderr).hexdigest(),'stderr_bytes':len(p.stderr),'funding':False,'submit':False}
if v['passed']:v['helper']=json.loads(p.stdout)
with (r/'state/install-process-receipt.json').open('x') as f:os.fchmod(f.fileno(),0o600);json.dump(v,f);f.flush();os.fsync(f.fileno())
print(json.dumps(v))
''';v=remote(role,code,305);save(role+'-standby-cwd-install-actual',v);results[role]=v;assert v['passed'],role+' isolated install failed'
   if role=='C':Cstarted=True
   else:Bstarted=True
  # Actual A-owned forced route, fixed host key, no administrative operation.
  route=binding['A_controller_route'];args=['ssh','-T','-F','/dev/null','-i',route['key'],'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+route['known_hosts'],'-o','HostKeyAlias='+route['host_key_alias'],'-o','ForwardAgent=no','-o','ClearAllForwardings=yes','-o','ConnectTimeout=10',route['target']]
  receipts={}
  for op in ['finite-checkpoint','status']:
   request={'action':'checkpoint'} if op=='finite-checkpoint' else {'action':'independent','op':'status','run_id':plan['standby_run_id']};p=subprocess.run(args,input=enc(request)+b'\n',capture_output=True,timeout=30);assert p.returncode==0;v=json.loads(p.stdout);assert 'error' not in v;receipts[op]=v
  s=receipts['status'];assert not s['events'] and not s['faulted'] and s['terminal_result'] is None and s['latest_probe']['all_reachable'] and not s['latest_probe']['uncertain'];save('A-standby-cwd-forced-route-actual',{'passed':True,'receipts':receipts,'funding':False,'submit':False})
  save('STANDBY-CWD-INSTALL-ACTUAL',{'passed':True,'run_id':plan['standby_run_id'],'roles':results,'authorized_keys_sha256':auth['authorized_keys_sha256'],'unarmed':True,'funding':False,'submit':False});print('Actual C/B standby and A forced route PASS; collector probe pending')
 except BaseException:
  # Only this invocation's new units/lines are affected. Historical units untouched.
  for role in ['B','C']:
   unit=binding[role]['unit'];save(role+'-standby-cwd-abort-stop',remote(role,'UNIT='+repr(unit)+'\n'+"import subprocess,json\np=subprocess.run(['systemctl','stop',UNIT],capture_output=True,timeout=200);print(json.dumps({'unit':UNIT,'stop_exit_code':p.returncode,'old_units_stopped':False}))",215))
  if added:
   code='ROOT='+repr(Croot)+'\nLINES='+repr(lines)+'\n'+r'''
import pathlib,json,os
r=pathlib.Path(ROOT);a=pathlib.Path('/var/lib/kpi-history/.ssh/authorized_keys');raw=a.read_bytes();pieces=raw.splitlines(keepends=True);targets=[x.encode() for x in LINES.values()];assert all(pieces.count(x)<=1 for x in targets)
with a.open('wb') as f:f.write(b''.join(x for x in pieces if x not in targets));f.flush();os.fsync(f.fileno())
pre=r/'state/authorized-keys.preimage';print(json.dumps({'exact_new_lines_removed':True,'old_auth_equals_preimage':pre.exists() and a.read_bytes()==pre.read_bytes()}))
''';save('C-standby-cwd-abort-route-cleanup',remote('C',code,25))
  raise
if __name__=='__main__':execute()
