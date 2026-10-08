"""Strict amount extraction from independently hash-bound reviewed native terms.
This checks integer/conservation metadata, not proof validity or live authority.
"""
import argparse,hashlib,json,pathlib,re
U64=2**64-1
FIELDS={'schema','network','manifest_sha256','reviewed','funding_fee_cap_sompi','maximum_wallet_debit_sompi'}
def require(x,m):
 if not x:raise ValueError(m)
def u64(v):
 require(type(v) is int or (type(v) is str and re.fullmatch(r'0|[1-9][0-9]*',v) is not None),'canonical integer amount');n=int(v);require(0<=n<=U64,'amount uint64 range');return n
CREDIT_POLICY_SOURCE=pathlib.Path('@KPI_REPO@/.local/worktrees/a1-poc/scripts/a1_fee_check.py')
CREDIT_POLICY_SHA256='e0228a996c9b9b5cbf725bd4c16adba8d5814b230faea6a71b6b4e2c72558d88'
def check_credit_policy(credit,fees):
 # Exact original a1_fee_check.py185 arithmetic. This inexpensive parameter
 # check precedes expensive proving; fresh fee/native/SDK checks remain required.
 raw=CREDIT_POLICY_SOURCE.read_bytes();require(hashlib.sha256(raw).hexdigest()==CREDIT_POLICY_SHA256,'original fee-credit policy source changed')
 require(b'required_credit = (11 * max(f0, fc + f1) + 9) // 10' in raw,'original fee-credit formula')
 require(set(fees)=={'s0_continue','s0_terminal','s1_terminal'},'exact native branch fees')
 f0=u64(fees['s0_terminal']);fc=u64(fees['s0_continue']);f1=u64(fees['s1_terminal']);b0=u64(credit);required=(11*max(f0,fc+f1)+9)//10
 require(required<=U64 and b0>=required,'original refundable fee-credit headroom')
 return {'required_credit_sompi':str(required),'credit_sompi':str(b0),'policy_source_sha256':CREDIT_POLICY_SHA256,'fresh_fee_or_native_validation_performed':False}

def extract(manifest,manifest_sha,review):
 require(set(review)==FIELDS and review['schema']=='kpi-reviewed-native-fixed-terms/v1' and review['network']=='testnet-10' and review['reviewed'] is True and review['manifest_sha256']==manifest_sha,'externally reviewed exact manifest terms')
 require(manifest['network']=='testnet-10' and set(manifest['states'])=={'s0','s1'} and set(manifest['branches'])=={'s0_continue','s0_terminal','s1_terminal'},'native finite branch/state schema')
 states={}
 for n,s in manifest['states'].items():
  vals={k:u64(s[k]) for k in ['L','B','R']};require(vals['R']==vals['L']+vals['B']<=U64 and vals['L']>0,'native reserve/credit conservation');states[n]=vals
 recipient=manifest['recipient']['spk_hex'];fees={};payout={}
 for n,b in manifest['branches'].items():
  source='s1' if n=='s1_terminal' else 's0';fee=u64(b['fee']);require(fee>0,'positive fixed fee');fees[n]=fee
  outputs=b['outputs'];require(len(outputs)==(2 if n=='s0_continue' else 1),'fixed branch output count');amounts=[u64(x['value']) for x in outputs]
  require(all(x['index']==str(i) and x['covenant'] is None for i,x in enumerate(outputs)) and sum(amounts)+fee==states[source]['R'],'native branch value conservation')
  require(outputs[-1]['spk_hex']==recipient,'predeclared recipient binding');payout[n]=amounts[-1]
  if n=='s0_continue':
   require(amounts[0]==states['s1']['R'] and outputs[0]['spk_hex']==manifest['states']['s1']['spk_hex'],'exact next-state output')
   require(all(u64(b['next_'+k])==states['s1'][k] for k in ['L','B','R']) and states['s0']['B']-fee==states['s1']['B'],'credit fee transition')
  else:require(all(u64(b['next_'+k])==0 for k in ['L','B','R']) and states[source]['B']>=fee,'terminal consumes credit with zero next state')
 check_credit_policy(str(states['s0']['B']),{k:str(v) for k,v in fees.items()})
 cap=u64(review['funding_fee_cap_sompi']);debit=u64(review['maximum_wallet_debit_sompi']);require(cap>0 and states['s0']['R']+cap==debit<=U64,'explicit exact funding/debit cap')
 return {'schema':'kpi-native-fixed-term-extraction/v1','manifest_sha256':manifest_sha,'network':'testnet-10','reserve_sompi':str(states['s0']['R']),'credit_sompi':str(states['s0']['B']),'funding_fee_cap_sompi':str(cap),'maximum_wallet_debit_sompi':str(debit),'branch_fees_sompi':{k:str(v) for k,v in fees.items()},'branch_recipient_payouts_sompi':{k:str(v) for k,v in payout.items()},'proof_verification_performed':False,'live_authorized':False}
def load(manifest_path,manifest_pin,review_path,review_pin):
 raw=pathlib.Path(manifest_path).read_bytes();rraw=pathlib.Path(review_path).read_bytes();require(hashlib.sha256(raw).hexdigest()==manifest_pin and hashlib.sha256(rraw).hexdigest()==review_pin,'external terms bytes changed');return extract(json.loads(raw),manifest_pin,json.loads(rraw))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--manifest-sha256',required=True);p.add_argument('--review',required=True);p.add_argument('--review-sha256',required=True);a=p.parse_args();print(json.dumps(load(a.manifest,a.manifest_sha256,a.review,a.review_sha256),sort_keys=True))
