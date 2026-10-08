"""C independently confirms and durably receipts S0. Never reads an S1 body."""
import pathlib,json,hashlib,os,sys
from launcher_common import E,BASE,remote
from controller_access import load_binding
R=BASE;D=E

def main():
 cfg,_,_=load_binding();binding=json.loads((D/'current-runtime-binding.json').read_text());installed=binding['C'];review=json.loads((D/'funding-review.json').read_text())
 assert review['txid']==cfg['locator']['s0_txid_hex']
 code=r'''import sys,pathlib,json,sqlite3,zlib,time,hashlib,os
for n,h in INSTALLED['source_pins'].items():
 p=pathlib.Path(INSTALLED['source_root'])/n;assert not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==h
sys.path.insert(0,INSTALLED['source_root']);from rpc_local import RPC;from a1_recovery import rpc_spk,rpc_uint,full_hash
p=pathlib.Path(INSTALLED['config_path']);assert not p.is_symlink();raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==CONFIG_PIN;cfg=json.loads(raw);assert cfg['run_id']==RUN and cfg['mode']=='finite-live-native' and cfg['execution_authorized']
loc=cfg['locator'];cp=cfg['checkpoint'];from finite_runtime import database,node_binding;node_binding(cfg);db=sqlite3.connect('file:'+str(database(cfg))+'?mode=ro',uri=True);meta={k:json.loads(v) for k,v in db.execute('SELECT key,value FROM metadata')};assert meta['last_error'] is None and time.time()-meta['last_commit']['at']<15
row=db.execute('SELECT a.page_seq,a.accepting_hash,b.body FROM acceptance a JOIN active_chain c ON c.hash=a.accepting_hash JOIN bodies b USING(full_hash) WHERE a.txid=? AND a.full_hash=? AND a.page_seq>? LIMIT 1',(loc['s0_txid_hex'],FULLHASH,cp['seq'])).fetchone()
if row is None:print(json.dumps({'ready':False,'reason':'C has not durably archived funding yet'}));raise SystemExit(0)
tx=json.loads(zlib.decompress(row[2]));assert tx['verboseData']['transactionId']==loc['s0_txid_hex'] and full_hash(tx)==FULLHASH
assert rpc_uint(tx['outputs'][0]['value'])==rpc_uint(loc['s0_amount']) and rpc_spk(tx['outputs'][0]['scriptPublicKey']).hex()==loc['s0_spk_hex'] and tx['outputs'][0].get('covenant') is None
obs=db.execute('SELECT at,page_seq,response_sha,response FROM utxo_observations ORDER BY seq DESC LIMIT 1').fetchone();assert obs and time.time()-obs[0]<15;body=zlib.decompress(obs[3]);assert hashlib.sha256(body).hexdigest()==obs[2];rows=json.loads(body)['entries'];matches=[x for x in rows if x['outpoint']=={'transactionId':loc['s0_txid_hex'],'index':0}]
if not matches:print(json.dumps({'ready':False,'reason':'C durable exact S0 UTXO observation not yet present'}));raise SystemExit(0)
assert len(matches)==1;entry=matches[0]['utxoEntry'];assert rpc_uint(entry['amount'])==rpc_uint(loc['s0_amount']) and rpc_spk(entry['scriptPublicKey']).hex()==loc['s0_spk_hex'] and entry['covenantId'] is None
rpc=RPC();info=rpc.call('getServerInfo',{});assert info['networkId']=='testnet-10' and info['isSynced'] and info['hasUtxoIndex'];allowed=cfg['finite']['watch_addresses'];now=rpc.call('getUtxosByAddresses',{'addresses':allowed});rpc.close();current=[x for x in now['entries'] if x['outpoint']=={'transactionId':loc['s0_txid_hex'],'index':0}];assert len(current)==1 and current[0]['utxoEntry']==entry
receipt={'schema':'kpi-g5-independent-durable-S0/v1','run_id':RUN,'at':time.time(),'funding_txid':loc['s0_txid_hex'],'funding_full_hash':FULLHASH,'S0_index':0,'amount_sompi':loc['s0_amount'],'accepting_block':row[1],'accepted_page_seq':row[0],'checkpoint_seq':cp['seq'],'current_C_commit':meta['last_commit'],'durable_historical_native_entry':entry,'current_exact_unspent':True,'active_accepting_chain':True,'scope':'independent validated C node and retained durable archive; not light-client finality'}
def persist_receipt(target,receipt):
 # Re-observation revalidates all current archive/chain/RPC checks above.
 # Preserve already-durable bytes; only observation time/commit may advance.
 if target.exists():
  data=target.read_bytes();prior=json.loads(data)
  assert set(prior)==set(receipt)
  for key in receipt:
   if key not in ('at','current_C_commit'):assert prior[key]==receipt[key], 'existing S0 receipt lineage mismatch'
  assert type(prior['at']) in (int,float) and 0<prior['at']<=receipt['at']
  return data,prior
 data=json.dumps(receipt,sort_keys=True,separators=(',',':')).encode();fd=os.open(target,os.O_EXCL|os.O_CREAT|os.O_WRONLY,0o600)
 # Root service owns this fresh finite directory; do not hardcode legacy capture UID.
 with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 fd=os.open(target.parent,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 return data,receipt
target=pathlib.Path(cfg['finite']['root'])/RUN/'S0-confirmation.json'
data,stored=persist_receipt(target,receipt)
print(json.dumps({'ready':True,'C_receipt_sha256':hashlib.sha256(data).hexdigest(),'receipt':stored}))
'''.replace('INSTALLED',repr(installed)).replace('CONFIG_PIN',repr(hashlib.sha256(json.dumps(cfg,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest())).replace('RUN',repr(cfg['run_id'])).replace('FULLHASH',repr(review['full_hash']))
 x=json.loads(remote.run('@C_SSH_HOST@',code,90))
 if x['ready']:
  target=D/'S0-confirmation.json';target.write_text(json.dumps(x,indent=2));target.chmod(0o600)
  print(json.dumps({'C_independent_S0_confirmation':True,'C_receipt_sha256':x['C_receipt_sha256'],'durable_historical_entry':True,'current_exact_unspent':True,'active_accepting_chain':True}))
 else:print(json.dumps(x))

if __name__=='__main__':main()
