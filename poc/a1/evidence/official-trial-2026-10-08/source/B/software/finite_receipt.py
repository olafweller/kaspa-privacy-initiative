"""B independently binds C authenticated finite evidence to pre-loss frozen pins.
No chain finality/light-client claim; missing shared pins fail closed.
"""
import hashlib,json,time,math,re
from pathlib import Path

def encode(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(v):return hashlib.sha256(encode(v)).hexdigest()
def require(ok,why):
 if not ok:raise ValueError(why)

def seal(config,value,expected_digest):
 expected=config['finite_expected']
 require(set(expected)=={'schema','run_id','network','genesis','server_version','config_sha256','role_sources_sha256','native_sha256','sdk_sha256','checkpoint_sha256'} and expected['schema']=='kpi-B-finite-expectations/v1' and expected['network']=='testnet-10','strict frozen B finite expectation schema')
 require(config['mode']=='finite-live-native' and value['schema']=='kpi-C-native-validated-prefix-seal/v1' and value['phase']=='s1' and value['network']=='testnet-10' and value['run_id']==config['run_id']==expected['run_id'],'finite seal phase/run')
 require(digest(value)==expected_digest,'finite seal digest')
 for target,source in [('config_sha256','config_sha256'),('role_sources_sha256','role_sources_sha256'),('native_sha256','native_sha256'),('sdk_sha256','sdk_sha256'),('genesis','genesis'),('server_version','server_version'),('checkpoint_sha256','checkpoint_sha256')]:
  require(value[target]==expected[source],'frozen finite '+target)
 require(value['continuation']['accepting_hash'] in value['active_chain'] and value['active_chain'][-1]==value['endpoint'],'finite accepting lineage')
 return value

def historical(config,source):
 s=seal(config,source['finite_seal'],source['finite_seal_sha256'])
 require(s['checkpoint_sha256']==digest(source['checkpoint']) and s['history_manifest_sha256']==source['history_manifest_sha256'] and s['prefix_sha256']==source['history_commit']['digest'] and s['endpoint']==source['history_commit']['cursor']==source['horizon'],'complete frozen finite history binding')
 return s

def uint(v,maximum=2**64-1):return type(v) is int and 0<=v<=maximum
def hexhash(v):return type(v) is str and re.fullmatch('[0-9a-f]{64}',v) is not None
def fields(v,names,why):require(type(v) is dict and set(v)==set(names.split()),why)
def survival(v,endpoint):
 fields(v,'removedChainBlockHashes addedChainBlockHashes acceptedTransactionIds','fixed survival fields')
 removed,added,accepted=(v[k] for k in ['removedChainBlockHashes','addedChainBlockHashes','acceptedTransactionIds'])
 require(type(removed) is list and not removed and type(accepted) is list and not accepted and type(added) is list and len(added)<=2480 and all(hexhash(h) for h in added) and len(set(added))==len(added) and endpoint not in added,'fixed endpoint survival')
def native_utxos(value,addresses):
 fields(value,'entries','native UTXO response fields');require(type(value['entries']) is list and len(value['entries'])<=8,'native UTXO budget');seen=set()
 for item in value['entries']:
  fields(item,'address outpoint utxoEntry','native UTXO fields');require(item['address'] in addresses,'native UTXO watched address')
  op,entry=item['outpoint'],item['utxoEntry'];fields(op,'transactionId index','native outpoint fields')
  require(hexhash(op['transactionId']) and uint(op['index'],2**32-1),'native outpoint types');key=(op['transactionId'],op['index']);require(key not in seen,'duplicate native outpoint');seen.add(key)
  fields(entry,'amount scriptPublicKey blockDaaScore isCoinbase covenantId','native entry fields')
  spk=entry['scriptPublicKey'];require(uint(entry['amount']) and uint(entry['blockDaaScore']) and type(entry['isCoinbase']) is bool and (entry['covenantId'] is None or hexhash(entry['covenantId'])) and type(spk) is str and 4<=len(spk)<=20004 and re.fullmatch('(?:[0-9a-f]{2})+',spk) is not None,'native entry wire/types')
def current(config,observation,source,output,requested_addresses,*,clock=time.time):
 s=historical(config,source);receipt=observation['finite_current_receipt'];actual=observation['finite_seal']
 require(actual==s and observation.get('seal',actual)==s,'current/historical seal mismatch')
 fields(receipt,'schema run_id seal_sha256 observer seq previous_digest started_at completed_at started_monotonic completed_monotonic duration observations trust digest','finite receipt fields')
 require(receipt['trust']=='sampled validating C node assertion; non-atomic RPC bracket' and hexhash(receipt['previous_digest']),'finite receipt contract')
 obs=receipt['observations'];fields(obs,'server_before server_after genesis request survival_before survival_after addresses utxos dag','finite observation fields')
 observer=receipt['observer'];fields(observer,'boot pid start_ticks','finite observer identity');require(type(observer['boot']) is str and len(observer['boot'])==36 and uint(observer['pid']) and observer['pid']>0 and uint(observer['start_ticks']),'finite observer identity types')
 body={k:v for k,v in receipt.items() if k!='digest'}
 for server in [obs['server_before'],obs['server_after']]:
  require(server['networkId']=='testnet-10' and server['serverVersion']==s['server_version'] and server['isSynced'] is True and server['hasUtxoIndex'] is True,'independent B node identity/health')
 require(type(receipt['seq']) is int and receipt['seq']>0,'finite observation sequence')
 require(receipt['digest']==digest(body) and receipt['schema']=='kpi-C-prefix-current-sample/v1' and receipt['run_id']==config['run_id'] and receipt['seal_sha256']==source['finite_seal_sha256'],'finite current digest/run binding')
 addresses=obs['addresses']
 require(type(addresses) is list and 1<=len(addresses)<=8 and all(type(a) is str and a.startswith('kaspatest:') and len(a)<=150 for a in addresses) and len(set(addresses))==len(addresses),'finite watched address set')
 require(type(requested_addresses) is list and 1<=len(requested_addresses)<=8 and all(type(a) is str and a in addresses for a in requested_addresses) and len(set(requested_addresses))==len(requested_addresses),'exact requested address subset')
 native_utxos(obs['utxos'],addresses);native_utxos(observation['utxos'],requested_addresses)
 filtered={'entries':[x for x in obs['utxos']['entries'] if x['address'] in requested_addresses]}
 require(filtered==observation['utxos'] and obs['server_after']==observation['server'],'requested native response differs from authenticated receipt')
 fields(obs['request'],'startHash includeAcceptedTransactionIds minConfirmationCount','fixed survival request fields')
 require(obs['request']['startHash']==s['endpoint'] and obs['request']['includeAcceptedTransactionIds'] is False and type(obs['request']['minConfirmationCount']) is int and obs['request']['minConfirmationCount']==0,'fixed survival request')
 for key in ['survival_before','survival_after']:survival(obs[key],s['endpoint'])
 require(obs['genesis']['genesis']==s['genesis'] and obs['genesis']['network']=='testnet-10','sample genesis binding')
 require(hexhash(obs['dag']['sink']) and uint(obs['dag']['virtualDaaScore']) and uint(obs['dag']['pastMedianTime']),'sample native DAG context')
 times=[receipt[k] for k in ['started_at','completed_at','started_monotonic','completed_monotonic','duration']]
 require(all(type(t) in [int,float] and math.isfinite(t) for t in times),'finite sample timestamps')
 now=clock();wall_delta=receipt['completed_at']-receipt['started_at'];mono_delta=receipt['completed_monotonic']-receipt['started_monotonic']
 require(-2<=now-receipt['started_at']<=15 and receipt['started_at']<=receipt['completed_at']<=now+2 and 0<=mono_delta<=8 and 0<=wall_delta<=8 and abs(wall_delta-mono_delta)<=1 and receipt['duration']==mono_delta,'current finite original timestamps')
 marker=Path(output)/'finite-observation-binding.json'
 value={'seal_sha256':receipt['seal_sha256'],'observer':receipt['observer'],'seq':receipt['seq'],'digest':receipt['digest']}
 if marker.exists():
  previous=json.loads(marker.read_bytes());require(previous['seal_sha256']==value['seal_sha256'] and previous['observer']==value['observer'] and value['seq']>=previous['seq'] and (value['seq']!=previous['seq'] or value['digest']==previous['digest']),'finite observer restart/regression/mixed sequence')
 # Local B recovery scratch only. C historical/public evidence remains unchanged.
 from durable_result import atomic
 atomic(marker,value)
 return receipt
