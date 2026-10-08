from a1_recovery import rpc_uint
"""B-authenticated sanitized result retention; no keys, bodies, RPC or submission API."""
import hashlib,json,re,time
from pathlib import PurePosixPath,Path
from terminal_sdk_gate import validate_receipt,validate_evidence,sha
SCHEMA='kpi-g5-autonomous-result/v1'
COMMON={'schema','run_id','mode','status','at','stage','broadcast','A_dependency'}
SUCCESS={'terminal_sdk_receipt','terminal_sdk_receipt_sha256','recovery_report','native_Full','fresh_proving','artifact_evidence','controller_events','C_event_digests','manifest_sha256','inventory_sha256','worker_source_sha256'}
REPORT={'SDK_roundtrip_decoded_native_Full','scope','mode','discovery','fresh_terminal_proof','separate_native_Full','A_access_required','broadcast','elapsed_seconds','current_observation_trust'}
DISCOVERY={'scope','lineage_history_complete','funding_body_verified','state','current_outpoint','paid','fees','cursor','transitions','terminal_spendability_demonstrated','live_tn10_demonstrated','independent_machine_loss_demonstrated','current_utxo_reconciled'}
FULL={'txid','full_hash','full_valid','fee','native_masses','consensus_full_hash_preimage_bytes','mass_scope'}
PROVE={'input_context_sha256','input_request_sha256','proof_sha256','witness_sha256','constructed_body_sha256','fresh_proof','native_full','txid','fee','elapsed_ms','scope'}
NAMES={'terminal-pre-sdk-full-validation.json','terminal-sdk-receipt.json','terminal-sdk-safe.json','terminal-sdk-numeric.json','terminal-sdk-decoded.json','terminal-sdk-decoded-request.json','terminal-sdk-native-full.json','fresh-terminal.json','full-request.json','terminal-request.json','report.json','terminal-proving-receipt.json','terminal-full-validation.json','independent-absence-receipt.json','archive/lineage-hint.json','archive/pages.json','archive/history-manifest.json','archive/current-entries.json','archive/current-utxos.json','archive/source.json','archive/entries.json','archive/locator.json','archive/current-observation.json','archive/provenance.json','archive/checkpoint.json'}
def require(v,m):
 if not v:raise ValueError(m)
def validate(result,cfg,rows,validation_at=None):
 require(result['schema']==SCHEMA and result['run_id']==cfg['run_id'] and result['mode']==cfg['mode'],'result run/schema mismatch')
 require(result['broadcast'] is False and result['A_dependency'] is False,'forbidden result behavior')
 now=time.time() if validation_at is None else validation_at
 require(type(now) in [int,float] and type(result['at']) in [int,float] and -2<=now-result['at']<300,'stale result')
 require(result['status'] in ['success','failure'],'unknown result status')
 if result['status']=='failure':
  require(set(result)==COMMON|{'reason'},'failure fields changed')
  require(result['reason'] in ['timeout','interrupted','guard_or_recovery_rejected','controller_rejected','service_terminated'],'unsafe failure detail')
  require(result['stage'] in ['startup','acceptance-wait','physical-shutdown-wait','fresh-proof-and-Full','terminal-Full-stop','systemd-stop'],'unknown failure stage');return
 require(set(result)==COMMON|SUCCESS and len(rows)==6,'success before completed loss/recovery gate')
 require(result['stage']=='terminal-Full-stop' and result['C_event_digests']==[x['digest'] for x in rows],'result boundary mismatch')
 for k in ['manifest_sha256','inventory_sha256','worker_source_sha256']:require(result[k]==cfg[k],'unfrozen result provenance')
 r=result['recovery_report'];d=r['discovery'];f=result['native_Full'];p=result['fresh_proving']
 require(set(r)==REPORT and set(d)==DISCOVERY and set(f)==FULL and set(p)==PROVE,'unknown report field; secret/evidence injection forbidden')
 require(d['state']=='s1' and d['lineage_history_complete'] is True and d['funding_body_verified'] is True and d['current_utxo_reconciled'] is True,'incomplete lineage')
 require(r['fresh_terminal_proof'] is True and r['separate_native_Full'] is True and r['SDK_roundtrip_decoded_native_Full'] is True and r['A_access_required'] is False and r['broadcast'] is False,'incomplete recovery')
 require(p['fresh_proof'] is True and p['native_full'] is True and f['full_valid'] is True and p['txid']==f['txid'] and rpc_uint(p['fee'])==rpc_uint(f['fee']),'terminal proof/Full mismatch')
 for value in [p['txid'],f['full_hash']]:require(isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value),'malformed native hash')
 evidence=result['artifact_evidence'];require(6<=len(evidence)<=128,'evidence cardinality budget')
 names=[]
 for e in evidence:
  require(set(e)=={'name','bytes','sha256'} and isinstance(e['name'],str) and '..' not in PurePosixPath(e['name']).parts and not e['name'].startswith('/'),'unsafe evidence name')
  require(e['name'] in NAMES or (cfg['mode']=='finite-live-native' and e['name']=='finite-observation-binding.json') or (e['name'].startswith('archive/') and re.fullmatch('archive/(page|observations)-[0-9]+.json',e['name'])),'unknown evidence file')
  require(type(e['bytes']) is int and 0<=e['bytes']<=16777216 and re.fullmatch('[0-9a-f]{64}',e['sha256']),'invalid evidence hash/size');names.append(e['name'])
 require(len(names)==len(set(names)) and {'fresh-terminal.json','report.json','terminal-proving-receipt.json','terminal-full-validation.json'}<=set(names),'missing/repeated evidence')
 if cfg.get('history_evidence_required'):
  from history_chunks import LIMIT,TARGET,digest
  if cfg['mode']=='finite-live-native':
   from finite_runtime import run_path
   root=run_path(cfg)/'history-evidence'
  else:root=Path('/var/lib/kpi-capture/boundary-final')/cfg['run_id']/'history-evidence'
  mp=root/'history-manifest.json';raw=mp.read_bytes();m=json.loads(raw)
  require(m['run_id']==cfg['run_id'],'history manifest run mismatch')
  expected=[{'name':'archive/history-manifest.json','bytes':len(raw),'sha256':digest(raw)}]
  actual=[e for e in evidence if e['name']=='archive/history-manifest.json' or re.fullmatch('archive/page-[0-9]+.json',e['name'])]
  require(sorted(actual,key=lambda x:x['name'])==sorted(expected,key=lambda x:x['name']),'B/C complete ordered history binding mismatch')
  require([x['index'] for x in m['chunks']]==list(range(len(m['chunks']))) and len({x['name'] for x in m['chunks']})==len(m['chunks']),'invalid ordered chunk manifest')
  require(all(0<x['bytes']<=TARGET<LIMIT for x in m['chunks']) and 'archive/pages.json' not in names,'bounded history evidence required')
 manifest_bytes=Path(cfg['manifest']).read_bytes();require(sha(manifest_bytes)==cfg['manifest_sha256'],'C frozen manifest hash changed');validate_receipt(result['terminal_sdk_receipt'],cfg,json.loads(manifest_bytes),f,p,d);validate_evidence(result['terminal_sdk_receipt'],result['terminal_sdk_receipt_sha256'],evidence)
 ev=result['controller_events'];require(len(ev)==4 and [x['kind'] for x in ev]==['B_CONTROLLER_STARTED_BEFORE_ACCEPTANCE','B_ARMED_AFTER_C_RECEIPT','B_RELEASED_AFTER_C_INDEPENDENT_LOSS','B_FRESH_TERMINAL_FULL_STOP_NO_BROADCAST'],'B order incomplete')
 require(ev[0]['at']<=rows[1]['at']+2 and rows[1]['at']<=ev[1]['at']+2 and ev[1]['at']<=rows[4]['at']+2 and rows[4]['at']<=ev[2]['at']+2 and ev[2]['at']<=ev[3]['at'],'B/C time ordering failed')
 for x in ev:require(set(x)=={'kind','at','payload'},'unexpected B marker')
 # Native/public report fields only. Report is private on B/C, not a public backup.
 text=json.dumps(result,sort_keys=True)
 require(len(text.encode())<=14000,'report request budget')
 for bad in ['claim-secret.bin','recipient-key.bin','unlock.key','PRIVATE KEY','ciphertext_b64','nonce_b64']:
  require(bad not in text,'secret/backup disclosure forbidden')
