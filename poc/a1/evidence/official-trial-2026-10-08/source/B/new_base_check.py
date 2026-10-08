"""Actual B UID999 check of new public/native/AES backup bytes; no network/proofs."""
import argparse,pathlib,sys,json,hashlib,base64,subprocess,tempfile,os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
P=pathlib.Path
sha=lambda p:hashlib.sha256(P(p).read_bytes()).hexdigest()
enc=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--config-sha256',required=True);a=p.parse_args();assert os.getuid()==999 and sha(a.config)==a.config_sha256;cfg=json.loads(P(a.config).read_bytes());assert all(cfg[k] is False for k in ['execution_authorized','terminal_execution_authorized','funding_authorized','poweroff_authorized'])
 sys.dont_write_bytecode=True;sys.path.insert(0,'/software');from a1_recovery_rehearsal import verify_inventory
 for n,h in cfg['effective_role_source_pins']['B'].items():assert sha(P('/software')/n)==h
 for n,h in cfg['native_binary_source_pins']['B'].items():assert sha(P('/software')/n)==h
 base=P('/instances')/cfg['base_instance_id'];public=base/'public';verify_inventory(public,cfg['inventory_sha256']);assert sha(public/'manifest.json')==cfg['manifest_sha256'];assert sha(base/'backup/backup-package.json')==cfg['backup_ciphertext_sha256']
 out=P('/work/finite-standby')/cfg['run_id']/'base-check';out.mkdir(mode=0o700,parents=True,exist_ok=False)
 result=subprocess.run(['/usr/bin/python3','-I','/software/a1_check.py',str(public),'--intent',str(public/'owner-intent.json'),'--receipt',str(public/'setup-receipt.json'),'--reference-binary','/software/a1_reference'],capture_output=True,timeout=110);assert result.returncode==0,'original independently wired public checker failed';checked=json.loads(result.stdout);assert checked['parameter_consistency'] is True
 (out/'public-checker.json').write_bytes(result.stdout);(out/'public-checker.json').chmod(0o600)
 pack=json.loads((base/'backup/backup-package.json').read_bytes());context={k:pack[k] for k in ['schema','run_id','manifest_sha256','artifact_inventory_sha256']};assert context['run_id']==cfg['base_instance_id'] and context['manifest_sha256']==cfg['manifest_sha256'] and context['artifact_inventory_sha256']==cfg['inventory_sha256'];key=(base/'backup/unlock.key').read_bytes();nonce=base64.b64decode(pack['nonce_b64'],validate=True);cipher=base64.b64decode(pack['ciphertext_b64'],validate=True);associated=enc(context);material=AESGCM(key).decrypt(nonce,cipher,associated);assert len(material)==64
 for kind in ['wrong-unlock','ciphertext','AAD']:
  try:AESGCM(bytes(32) if kind=='wrong-unlock' else key).decrypt(nonce,bytes([cipher[0]^1])+cipher[1:] if kind=='ciphertext' else cipher,associated+b'!' if kind=='AAD' else associated)
  except InvalidTag:pass
  else:raise ValueError('unauthenticated backup accepted')
 with tempfile.TemporaryDirectory(prefix='restore-',dir=out) as temp:
  d=P(temp);d.chmod(0o700)
  for n,raw in [('claim-secret.bin',material[:32]),('recipient-key.bin',material[32:])]:p=d/n;p.write_bytes(raw);p.chmod(0o600)
  native=subprocess.run(['/software/kpi-poc-a1','check-backup',str(public),str(d/'claim-secret.bin'),str(d/'recipient-key.bin')],capture_output=True,timeout=10);assert native.returncode==0,'original native backup check failed'
 receipt={'passed':True,'run_id':cfg['run_id'],'base_instance_id':cfg['base_instance_id'],'manifest_sha256':cfg['manifest_sha256'],'inventory_sha256':cfg['inventory_sha256'],'actual_UID':os.getuid(),'original_public_parameter_checker':True,'AES_authentication_and_native_correspondence':True,'wrong_unlock_tamper_AAD_rejected':True,'restore_deleted':True,'network_scope':'PrivateNetwork,no external network','new_proof_or_setup':False,'funding':False,'submit':False};(out/'receipt.json').write_bytes(enc(receipt));(out/'receipt.json').chmod(0o600);print(json.dumps(receipt))
if __name__=='__main__':main()
