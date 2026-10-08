"""Fresh B-owned/A-owned SSH credentials for this one false-authority standby.
No authorization lines, service, observer, capture, wallet or transaction.
"""
from pathlib import Path
import sys,json,hashlib,subprocess,os
W=Path(__file__).resolve().parent;T=W.parent;P=T/'package-standby-cwd';Q=Path('@KPI_REPO@/.local/g5-preparation/orchestrator-dedicated-B-fresh-preparation-20261007T045400Z');sys.path.insert(0,str(Q));import dedicated_remote,remote_safety
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();enc=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def save(p,v):
 with Path(p).open('xb') as f:os.fchmod(f.fileno(),0o600);f.write(enc(v));f.flush();os.fsync(f.fileno())
def execute():
 release=json.loads((W/'ROOT-STANDBY-CWD-RELEASE.json').read_bytes());assert release['credentials_source_sha256']==sha(__file__);plan=json.loads((P/'STAGE-PLAN.json').read_bytes());run=plan['standby_run_id'];creds=plan['B_credential_root']
 code='ROOT='+repr(creds)+'\n'+r'''
import pathlib,subprocess,os,hashlib,json
r=pathlib.Path(ROOT);assert not r.exists();r.mkdir(mode=0o700);os.chown(r,0,988);os.chmod(r,0o700);key=r/'id_ed25519'
subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(key),'-C','kpi-startup-step2-B'],check=True,capture_output=True,timeout=10);key.chmod(0o600);os.chown(key,999,988);print(json.dumps({'public':(r/'id_ed25519.pub').read_text().strip(),'key_sha256':hashlib.sha256(key.read_bytes()).hexdigest()}))
'''
 b=json.loads(dedicated_remote.run('@B_SSH_HOST@',remote_safety.wrap(code,'B','credentials'),20));private=T/'package/A/private';akey=private/'standby-controller_ed25519';assert not akey.exists();subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(akey),'-C','kpi-startup-step2-controller'],check=True,capture_output=True,timeout=10);akey.chmod(0o600)
 code='EXPECTED_A_PEER='+repr(plan['A_source_address'])+'\n'+r'''
import pathlib,os,json,hashlib
p=pathlib.Path('/var/lib/kpi-history/.ssh/authorized_keys');peer=os.environ['SSH_CONNECTION'].split()[0];assert peer==EXPECTED_A_PEER;host=pathlib.Path('/etc/ssh/ssh_host_ed25519_key.pub').read_text().strip();print(json.dumps({'authorized_keys_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'host_public_key':host,'A_source_address':peer}))
'''
 node=json.loads(dedicated_remote.run('@C_SSH_HOST@',remote_safety.wrap(code,'C','credentials-readonly'),20));assert node['authorized_keys_sha256']==plan['C_authorized_keys_preimage_sha256'];alias='tn10-finite-'+run;knownraw=(alias+' '+' '.join(node['host_public_key'].split()[:2])+'\n').encode();known=private/'standby-controller-known_hosts'
 with known.open('xb') as f:os.fchmod(f.fileno(),0o600);f.write(knownraw);f.flush();os.fsync(f.fileno())
 access={'target':'kpi-history@@C_ADDRESS@','host_key_alias':alias};bpins={'access.json':hashlib.sha256(enc(access)).hexdigest(),'known_hosts':hashlib.sha256(knownraw).hexdigest(),'id_ed25519':b['key_sha256']}
 code='ROOT='+repr(creds)+'\nACCESS='+repr(enc(access))+'\nKNOWN='+repr(knownraw)+'\n'+r'''
import pathlib,os,json
r=pathlib.Path(ROOT)
for name,raw in [('access.json',ACCESS),('known_hosts',KNOWN)]:
 with (r/name).open('xb') as f:os.fchown(f.fileno(),0,988);os.fchmod(f.fileno(),0o440);f.write(raw);f.flush();os.fsync(f.fileno())
print(json.dumps({'B_credential_inputs_staged':True,'private_key_never_exported':True}))
'''
 save(W/'B-new-credentials-staged.private.json',json.loads(dedicated_remote.run('@B_SSH_HOST@',remote_safety.wrap(code,'B','credentials-inputs'),20)))
 # The binder generates exact forced commands from authenticated FINAL C bytes.
 # Keep only independently observed peer/public-key fields; no provisional key lines.
 save(W/'STANDBY-ROUTE-KEYS.private.json',{'public_keys':{'B':b['public'],'controller':(private/'standby-controller_ed25519.pub').read_text().strip()},'peers':{'B':plan['B_source_address'],'controller':node['A_source_address']},'B_credential_pins':bpins,'C_authorized_keys_preimage_sha256':node['authorized_keys_sha256']})
 O=Path('@KPI_REPO@/.local/g5-preparation/orchestrator-finite-launch-preparation-20261007T101055Z');old=json.loads((W/'BASELINE-BINDING.private.json').read_bytes());old['A_controller_route'].update(key=str(akey),key_sha256=sha(akey),known_hosts=str(known),known_hosts_sha256=sha(known),host_key_alias=alias);old['A_credential_root']=str(private);save(W/'STANDBY-INSTALL-BINDING.private.json',old)
 print('Fresh dedicated credentials staged; no forced lines/services')
if __name__=='__main__':execute()
