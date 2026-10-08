from a1_recovery import rpc_uint
"""Strict sanitized terminal SDK receipt binding, shared by B and C. No RPC."""
import hashlib,json,re
SDK_PINS={'package.json':'8b61fefaba842c41b805291d95b2f9e81778ec590813a6c34eddcd316659b8d0','kaspa.js':'6d92cb305d0cc2eb26de9e305b7f7a8c17daa130ad478f0b340b50490557dbcf','kaspa_bg.wasm':'c9657568610ae1d305bc2e1cf85208ceba0d1a7893c4057b38caa8add2ffb0f5'}
NODE_PIN={'version':'v20.20.0','sha256':'d01614ef369e36eee9ab8d86fbfa93ddf44931010add45e5262a63e3ddda784e'}
SCHEMA='kpi-terminal-sdk-qualification/v1'
FIELDS=set('schema run_id branch instance_sha256 manifest_sha256 inventory_sha256 sdk runtime sources serialized_body_sha256 serialized_numeric_sha256 constructed_file_sha256 constructed_body_sha256 decoded_body_sha256 decoded_request_sha256 txid full_hash input_outpoint input_amount input_context_sha256 input_request_sha256 payout recipient_spk_sha256 output_count ordered_outputs_sha256 fee compute_budget native_masses proof_sha256 proof_bytes witness_sha256 artifact_bindings native_full_sha256 roundtrip_valid decoded_native_full_valid'.split())
def encode(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(value):return hashlib.sha256(value).hexdigest()
def require(v,m):
 if not v:raise ValueError(m)
def outputs(manifest,branch):return [{'value':x['value'],'scriptPublicKey':x['spk_hex'],'covenant':x['covenant']} for x in manifest['branches'][branch]['outputs']]
def input_context(entry):return {'amount':str(rpc_uint(entry['amount'])),'scriptPublicKey':entry['scriptPublicKey'],'blockDaaScore':str(rpc_uint(entry['blockDaaScore'])),'isCoinbase':entry['isCoinbase'],'covenantId':entry['covenantId']}
def bindings(manifest,branch):
 b=manifest['branches'][branch];return {k+'_sha256':b[k]['sha256'] for k in ['pk','vk','r1cs']}|{'context_sha256':b['context_sha256'],'redeem_sha256':manifest['states'][branch[:2]]['redeem']['sha256']}
def validate_receipt(r,cfg,manifest,full,proving,discovery):
 require(isinstance(r,dict) and set(r)==FIELDS,'SDK receipt fields/duplicates/mixed receipt')
 branch='s1_terminal';require(r['schema']==SCHEMA and r['branch']==branch and discovery['state']=='s1','wrong SDK schema/branch')
 require(r['run_id']==cfg['run_id'] and r['manifest_sha256']==cfg['manifest_sha256'] and r['inventory_sha256']==cfg['inventory_sha256'],'SDK run/instance/inventory mismatch')
 require(r['instance_sha256']==sha(bytes.fromhex(manifest['instance_hex'])),'SDK instance mismatch')
 require(r['sdk']=={'version':'2.1.0','files_sha256':SDK_PINS} and r['runtime']==NODE_PIN,'SDK/runtime pins mismatch')
 require(r['sources']==cfg['terminal_sdk_sources_sha256'],'SDK qualification source/runtime mismatch')
 require(r['roundtrip_valid'] is True and r['decoded_native_full_valid'] is True and full['full_valid'] is True,'decoded SDK/native Full missing')
 require(r['txid']==full['txid']==proving['txid'] and r['full_hash']==full['full_hash'],'SDK txid/full hash mismatch')
 require(rpc_uint(r['fee'])==rpc_uint(full['fee'])==rpc_uint(proving['fee'])==rpc_uint(manifest['branches'][branch]['fee']),'SDK fee mismatch')
 require(type(r['compute_budget']) is int and r['compute_budget']==int(manifest['envelope']['compute_budgets'][branch]),'SDK budget mismatch')
 require(r['native_masses']==full['native_masses'] and set(r['native_masses'])=={'compute','storage','transient'} and all(type(v) is int and v>=0 for v in r['native_masses'].values()),'SDK masses mismatch')
 require(r['input_outpoint']==list(discovery['current_outpoint']) and rpc_uint(r['input_amount'])==rpc_uint(manifest['states']['s1']['R']),'SDK input/amount mismatch')
 want=outputs(manifest,branch);require(len(want)==1 and r['output_count']==1 and rpc_uint(r['payout'])==rpc_uint(want[0]['value']) and want[0]['scriptPublicKey']==manifest['recipient']['spk_hex'] and want[0]['covenant'] is None,'SDK payout/count/metadata mismatch')
 require(r['ordered_outputs_sha256']==sha(encode(want)) and r['recipient_spk_sha256']==sha(bytes.fromhex(manifest['recipient']['spk_hex'])),'SDK output/order/recipient mismatch')
 require(r['artifact_bindings']==bindings(manifest,branch),'SDK VK/PK/R1CS/context/redeem bindings mismatch')
 require(r['proof_bytes']==128 and r['constructed_body_sha256']==r['decoded_body_sha256']==proving['constructed_body_sha256'] and r['proof_sha256']==proving['proof_sha256'] and r['witness_sha256']==proving['witness_sha256'],'SDK proof/body changed')
 require(r['input_context_sha256']==proving['input_context_sha256'] and r['input_request_sha256']==proving['input_request_sha256'],'SDK input context differs from independent construction')
 require(r['native_full_sha256']==sha(encode(full)),'decoded Full receipt mismatch')
 for k,v in r.items():
  if k.endswith('_sha256') or k in ['txid','full_hash']:require(isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v),'malformed SDK receipt hash')
 require(len(encode(r))<6000,'SDK receipt size budget')
def validate_evidence(r,digest,evidence):
 require(digest==sha(encode(r)),'mixed SDK receipt digest')
 names=[e['name'] for e in evidence];require(len(names)==len(set(names)),'duplicate SDK/evidence receipt')
 index={e['name']:e['sha256'] for e in evidence};expected={'terminal-sdk-receipt.json':digest,'terminal-request.json':r['input_request_sha256'],'fresh-terminal.json':r['constructed_file_sha256'],'terminal-sdk-safe.json':r['serialized_body_sha256'],'terminal-sdk-numeric.json':r['serialized_numeric_sha256'],'terminal-sdk-decoded.json':r['decoded_body_sha256'],'terminal-sdk-decoded-request.json':r['decoded_request_sha256'],'terminal-sdk-native-full.json':r['native_full_sha256'],'terminal-full-validation.json':r['native_full_sha256']}
 require(all(index.get(k)==v for k,v in expected.items()),'missing/mixed SDK artifact evidence')
