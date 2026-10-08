"""Synthetic TestConsensus fixture receipt binding, never a live header oracle.

Hashing a receipt does not authenticate its producer: the caller must pin and
execute the separately reviewed fixture adapter. Unit fixtures are synthetic.
"""
import copy,hashlib,json,re
import a1_recovery as r
from historical_context import checked_entry

def require(ok,msg):
 if not ok:raise ValueError(msg)
def encode(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(value):return hashlib.sha256(encode(value)).hexdigest()
def hex32(value):require(type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None,'noncanonical fixture hash');return value
def score(value):
 require(type(value) is str and re.fullmatch('0|[1-9][0-9]*',value) is not None,'noncanonical header DAA')
 require(int(value)<2**64,'header DAA overflow');return value
def membership(item):
 data=item['acceptance_data'];require(type(data) is list,'acceptance schema')
 matches=0
 for block in data:
  require(type(block) is dict and type(block.get('accepted_transactions')) is list,'acceptance block schema')
  for accepted in block['accepted_transactions']:
   require(type(accepted) is dict,'acceptance entry schema')
   if accepted.get('transaction_id')==item['transaction']['id']:matches+=1
 require(matches==1,'missing/duplicate native acceptance membership')
def header(item):
 h=item.get('accepting_header');require(type(h) is dict and set(h)=={'hash','daa_score'},'missing native accepting header')
 require(hex32(h['hash'])==hex32(item['accepting_block']),'accepting header hash mismatch')
 return {'hash':h['hash'],'daaScore':score(h['daa_score'])}
def bind(result,request,adapter_sha256,source_patch_sha256):
 hex32(adapter_sha256);hex32(source_patch_sha256)
 require(type(request) is dict and set(request)=={'transactions','initial_entry'},'fixture request schema')
 steps=result.get('accepted_path');txs=request['transactions']
 require(type(steps) is list and type(txs) is list and 1<=len(steps)==len(txs)<=2,'fixture path length')
 hex32(result['synthetic_genesis_hash'])
 for i,(item,tx) in enumerate(zip(steps,txs)):
  header(item);membership(item);hex32(item['block']);hex32(tx['id']);checked_entry(item['input_entry'])
  require(item['transaction']['id']==tx['id'] and r.canonical_body(item['transaction'])==r.canonical_body(tx),'native stored body differs from exact fixture request')
  require(len(tx['inputs'])==1,'fixture single input required')
  if i==0:require(item['input_entry']==request['initial_entry'],'native initial seed mismatch')
  else:
   prior=steps[i-1];point=tx['inputs'][0]['previousOutpoint']
   require(point['transactionId']==prior['transaction']['id'] and type(point['index']) is int and 0<=point['index']<len(prior['transaction']['outputs']),'fixture continuation outpoint mismatch')
   output=prior['transaction']['outputs'][point['index']];entry=item['input_entry']
   require(r.rpc_uint(entry['amount'])==r.rpc_uint(output['value']) and r.rpc_spk(entry['scriptPublicKey'])==r.rpc_spk(output['scriptPublicKey']) and entry['covenantId'] is None and output['covenant'] is None and entry['isCoinbase'] is False,'fixture prior output terms mismatch')
   require(type(entry['blockDaaScore']) is int and entry['blockDaaScore']==int(prior['accepting_header']['daa_score']),'fixture prior output/header DAA mismatch')
 receipt=copy.deepcopy(result)
 return {'schema':'kpi-native-fixture-header-provenance/v1','adapter_sha256':adapter_sha256,'source_patch_sha256':source_patch_sha256,'request_sha256':digest(request),'receipt_sha256':digest(receipt),'request':copy.deepcopy(request),'receipt':receipt}
def verify(envelope,adapter_sha256,source_patch_sha256):
 require(type(envelope) is dict and set(envelope)=={'schema','adapter_sha256','source_patch_sha256','request_sha256','receipt_sha256','request','receipt'},'fixture envelope schema')
 rebuilt=bind(envelope['receipt'],envelope['request'],adapter_sha256,source_patch_sha256)
 require(envelope==rebuilt,'fixture provenance digest/pin mismatch');return envelope['receipt']
def stable_prefix(initial,accepted,adapter_sha256,source_patch_sha256):
 first=verify(initial,adapter_sha256,source_patch_sha256);second=verify(accepted,adapter_sha256,source_patch_sha256)
 require(first['synthetic_genesis_hash']==second['synthetic_genesis_hash'] and first['accepted_path'][0]==second['accepted_path'][0],'fixture funding prefix changed')
 require(initial['request']['initial_entry']==accepted['request']['initial_entry'],'fixture seed changed')

def stored(accepted,initial,adapter_sha256,source_patch_sha256):
 envelope=accepted.get('fixture_provenance');receipt=verify(envelope,adapter_sha256,source_patch_sha256)
 require({k:v for k,v in accepted.items() if k!='fixture_provenance'}==receipt,'stored native receipt changed')
 stable_prefix(initial['fixture_provenance'],envelope,adapter_sha256,source_patch_sha256)
 return receipt

def entries(receipt):
 out={}
 for item in receipt['accepted_path']:
  point=item['transaction']['inputs'][0]['previousOutpoint'];key=point['transactionId']+':'+str(point['index'])
  require(key not in out,'duplicate fixture input context');out[key]=item['input_entry']
 return out
