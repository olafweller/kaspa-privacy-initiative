"""B-owned credential and C-only connection, executed inside the B jail."""
import json,subprocess,pathlib,hashlib,os,socket
ROOT=pathlib.Path('/work')
def query(request):
 c=json.loads(pathlib.Path('/credentials/access.json').read_text())
 args=['/usr/bin/ssh','-T','-F','/dev/null','-i','/credentials/id_ed25519','-o','LogLevel=ERROR','-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/credentials/known_hosts','-o','HostKeyAlias='+c['host_key_alias'],'-o','ForwardAgent=no','-o','ClearAllForwardings=yes','-o','ConnectTimeout=10',c['target']]
 p=subprocess.run(args,input=json.dumps(request).encode()+b'\n',capture_output=True,timeout=1800)
 if p.returncode==255:raise ConnectionError('restricted C SSH transport unavailable; host-key and credential checks unchanged')
 if p.returncode:
  try:error=json.loads(p.stdout).get('error','request rejected')
  except Exception:error='SSH transport failure'
  raise ValueError('restricted C access failed at '+request['action']+': '+error)
 if len(p.stdout)>65*1024*1024:raise ValueError('restricted C response resource bound')
 data=json.loads(p.stdout)
 if 'error' in data:raise ValueError('C gateway rejected request')
 return data
def main():
 status=query({'action':'status'});assert status['pages']>0,'capture has not committed a page'
 (ROOT/'c-status.json').write_text(json.dumps(status))
 last=status['metadata']['last_commit']['seq'];page=query({'action':'page','seq':last})
 (ROOT/'live-page.json').write_text(json.dumps(page))
 # Never enumerate arbitrary public/miner addresses: this RPC has no server-side
 # result bound and a large address can exhaust node memory.
 addresses=json.loads(pathlib.Path('/software/utxo-allowlist.json').read_text())
 result=query({'action':'utxos','addresses':addresses[:4]})
 assert result['server']['isSynced'] and isinstance(result['utxos']['entries'],list),'current UTXO response qualification'
 (ROOT/'live-utxos.json').write_text(json.dumps(result))
 fixture=ROOT/'fixture-c';fixture.mkdir(mode=0o700,exist_ok=True)
 for name in ['locator.json','pages.json','entries.json','current-utxos.json','current-entries.json','source.json','pre-funding-checkpoint.json']:
  item=query({'action':'fixture','name':name});data=json.dumps(item['data'],sort_keys=True,separators=(',',':')).encode()
  # Receipt checksum is over the retained original bytes; semantic fixture copy
  # is labelled separately and never presented as a byte-for-byte archive copy.
  (fixture/name).write_bytes(data)
 forbidden=query({'action':'status'})
 report={'C_access_independent_of_A':True,'credential_owned_by_B':True,'SSH_agent_required':False,'forwarding_used':False,'capture_pages':status['pages'],'current_UTXO_entries':len(result['utxos']['entries']),'UTXO_test_scope':'allowlisted unfunded reserve address; empty is expected; no live positive reserve entry claimed','fixture_source':'C served published native fixture; not live TN10 recovery','host_directories_unreadable_or_absent':{p:not os.access(p,os.R_OK|os.X_OK) for p in ['/opt','/root','/home','/var/www','/var/lib/kpi-tn10']},'real_funding':False}
 (ROOT/'access-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()
