"""C-only read-only checkpoint export; capture readiness grants no execution authority."""
import pathlib, json
from horizon_gate import require_ready, value, check
from capacity import Capacity

def checkpoint(db, cfg, controller, rpc_factory, inspect_worker=True):
 check(cfg['namespace'].startswith('capture-a2-'), 'attempt namespace required')
 actual=db.execute('pragma database_list').fetchone()[2]
 check(pathlib.Path(actual).resolve()==pathlib.Path(cfg['database']).resolve(), 'reader database/config mismatch')
 db.execute('BEGIN')
 try:
  readiness=require_ready(db,cfg['namespace'],inspect_worker=inspect_worker,require_watch=controller['mode']=='live')
  last_request=json.loads(db.execute('select request from pages where seq=?',(readiness['current']['seq'],)).fetchone()[0]);check(last_request['minConfirmationCount']==0 and last_request['dataVerbosityLevel']=='Full','capture has unprocessed added range; funding checkpoint forbidden')
  capacity=Capacity(cfg).snapshot(db)
  check(capacity['prefunding_capacity_sufficient'],'attempt capture finite capacity insufficient')
  if controller['mode']=='live':
   watch=value(db,'watch_binding')
   check(watch['run_id']==controller['base_instance_id'] and watch['manifest_sha256']==controller['manifest_sha256'] and watch['inventory_sha256']==controller['inventory_sha256'],'capture watch/controller run binding mismatch')
   check(controller['capture_namespace']==cfg['namespace'] and controller['capture_baseline_receipt_sha256']==readiness['baseline_receipt_sha256'] and controller['capture_sealed_checkpoint_sha256']==readiness['sealed_checkpoint_sha256'],'capture/controller horizon binding mismatch')
  cp=readiness['sealed_checkpoint']
  rpc=rpc_factory()
  try:
   server=rpc.call('getServerInfo',{})
   check(server['networkId']=='testnet-10' and server['serverVersion']=='2.1.0' and server['isSynced'] and server['hasUtxoIndex'],'node not qualified')
   block=rpc.call('getBlock',{'hash':cp['cursor'],'includeTransactions':False})['block']
   check(block['verboseData']['isChainBlock'] and str(block['header']['blueScore'])==cp['blue_score'] and str(block['header']['daaScore'])==cp['daa_score'],'sealed retained checkpoint no longer selected')
  finally:rpc.close()
  return {k:cp[k] for k in ['schema','seq','cursor','digest','blue_score','daa_score','network','server_version']}|{'capture_namespace':cfg['namespace'],'capture_state':'READY','baseline_receipt_sha256':readiness['baseline_receipt_sha256'],'sealed_checkpoint_sha256':readiness['sealed_checkpoint_sha256'],'initialization_complete_page_sha256':readiness['initialization_complete_page_sha256'],'capture_horizon_source_sha256':value(db,'horizon_state')['horizon_source_sha256'],'funding_authorization':False,'scope':'bounded run-scoped C history from the sealed checkpoint; no pruning-survival or indefinite historical-recovery claim; read-only readiness qualification, separate live funding authorization required'}
 finally:db.rollback()
