"""Exact retained native context for the verified bounded ordinary-funding S0 path.
Not a latest-observation policy, a wallet resolver, or a chain-verification API.
The indexed discovery caller authenticates the complete frozen range and active
acceptance generation before attaching verified_funding_context to its callback.
"""
import copy,hashlib,json,zlib
import a1_recovery as r

MAX_OUTPOINTS=50000
MAX_VARIANTS_PER_OUTPOINT=32
MAX_TOTAL_VARIANTS=100000
MAX_ENCODED_BYTES=64*1024*1024
REQUIRED={'amount','scriptPublicKey','blockDaaScore','isCoinbase','covenantId'}

def encode(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def checked_entry(entry):
 r.require(isinstance(entry,dict) and REQUIRED==set(entry),'incomplete native context')
 if isinstance(entry['scriptPublicKey'],dict):r.require(set(entry['scriptPublicKey'])=={'version','script'},'native SPK schema')
 r.rpc_uint(entry['amount']);r.rpc_uint(entry['blockDaaScore']);r.rpc_spk(entry['scriptPublicKey'])
 r.require(type(entry['isCoinbase']) is bool,'malformed coinbase flag')
 r.require(entry['covenantId'] is None or isinstance(entry['covenantId'],str),'malformed covenant field')
 if entry['covenantId'] is not None:r.unhex(entry['covenantId'],32)
 return {k:v for k,v in entry.items() if k!='blockDaaScore'}

class Variants:
 def __init__(self):self.values={};self.count=0;self.bytes=0
 def __len__(self):return len(self.values)
 def add(self,point,entry):
  r.require(isinstance(point,dict) and set(point)=={'transactionId','index'},'malformed native outpoint')
  r.unhex(point['transactionId'],32);index=r.rpc_uint(point['index'],32)
  key=point['transactionId']+':'+str(index);immutable=checked_entry(entry)
  value=encode(entry);score=r.rpc_uint(entry['blockDaaScore'])
  if key in self.values:
   bucket=self.values[key]
   r.require(checked_entry(next(iter(bucket.values())))==immutable,'conflicting immutable native context')
   if score in bucket:
    r.require(bucket[score]==entry,'ambiguous exact native context representation');return
  else:
   r.require(len(self.values)<MAX_OUTPOINTS,'native context outpoint limit');bucket={}
  r.require(len(bucket)<MAX_VARIANTS_PER_OUTPOINT and self.count<MAX_TOTAL_VARIANTS and self.bytes+len(value)<=MAX_ENCODED_BYTES,'native context retention limit')
  bucket[score]=copy.deepcopy(entry);self.values[key]=bucket;self.count+=1;self.bytes+=len(value)
 def select(self,point,score):
  score=r.rpc_uint(score);key=point[0]+':'+str(r.rpc_uint(point[1],32));r.unhex(point[0],32)
  r.require(key in self.values and score in self.values[key],'exact active historical context not retained')
  return copy.deepcopy(self.values[key][score])
 def export(self):return {'schema':'kpi-observed-native-context-variants/v1','entries':{k:list(v.values()) for k,v in self.values.items()}}
 @classmethod
 def load(cls,data):
  r.require(isinstance(data,dict) and set(data)=={'schema','entries'} and data['schema']=='kpi-observed-native-context-variants/v1' and isinstance(data['entries'],dict),'native context archive schema')
  out=cls()
  for key,items in data['entries'].items():
   r.require(isinstance(key,str) and ':' in key and isinstance(items,list) and bool(items),'native context archive key/variants')
   tid,index=key.rsplit(':',1);idx=r.decimal(index,32)
   for entry in items:out.add({'transactionId':tid,'index':idx},entry)
  return out
 @classmethod
 def from_database(cls,db,after):
  out=cls()
  for checksum,blob in db.execute('SELECT response_sha,response FROM utxo_observations WHERE page_seq>? ORDER BY seq',(after,)):
   raw=zlib.decompress(blob);r.require(hashlib.sha256(raw).hexdigest()==checksum,'corrupt native observation')
   response=json.loads(raw);r.require(isinstance(response,dict) and isinstance(response.get('entries'),list),'native observation entries')
   for item in response['entries']:out.add(item['outpoint'],item['utxoEntry'])
  return out

def native_callback_from_variants(factory,binary,reference,variants):
 def validate(tx,context):
  if context is None:return factory(binary,reference,{})(tx,None)
  proof=context.get('verified_funding_context')
  r.require(isinstance(proof,dict) and context['state']=='s0' and proof['outpoint']==list(context['outpoint']),'verified active funding context required')
  r.unhex(proof['accepting_hash'],32);r.require(type(proof['accepting_page_seq']) is int and proof['checkpoint']['seq']<proof['accepting_page_seq']<=proof['commit']['seq'],'historical context generation binding')
  entry=variants.select(context['outpoint'],proof['block_daa_score'])
  r.require(entry['isCoinbase'] is False,'ordinary funding context marked coinbase')
  expected=context['bundle']['states']['s0'];r.require(r.rpc_uint(entry['amount'])==r.decimal(expected['R']) and r.rpc_spk(entry['scriptPublicKey']).hex()==expected['spk_hex'] and entry['covenantId'] is None,'wrong historical reserve entry')
  key=context['outpoint'][0]+':'+str(context['outpoint'][1])
  return factory(binary,reference,{key:entry})(tx,context)
 validate.requires_verified_funding_context=True
 return validate
