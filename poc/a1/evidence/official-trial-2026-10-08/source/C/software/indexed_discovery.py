"""Bounded G5 hint verification, not a general wallet/history replay engine."""
import hashlib,time
import a1_check as c
import a1_recovery as r
from history_chunks import canonical,iter_pages

def discover(pages,locator,bundle,inventory,native,hint,checkpoint,commit,run_id,emit=lambda *args:None):
 c.require(hint['schema']=='kpi-bounded-S0-spend-hint/v1' and hint['run_id']==run_id,'wrong index run/schema')
 c.require(hint['checkpoint_seq']==checkpoint['seq'] and hint['checkpoint_cursor']==checkpoint['cursor'] and hint['checkpoint_digest']==checkpoint['digest'] and hint['commit']==commit,'stale/gapped index binding')
 c.require(hint['S0_outpoint']==[locator['s0_txid_hex'],int(locator['s0_index'])],'wrong indexed old S0')
 funding=hint['funding'];spender=hint['spender'];refs=[funding,spender]
 c.require(funding['txid']==locator['s0_txid_hex'] and funding['txid']!=spender['txid'],'duplicate/wrong funding-spender hint')
 chain=[];generation={};found={};found_headers={};page_seq=checkpoint['seq'];cursor=checkpoint['cursor'];start=time.monotonic()
 for page in pages:
  page_seq+=1;c.require(page['startHash']==cursor,'retained cursor gap')
  response=page['response'];added=response['addedChainBlockHashes'];removed=response['removedChainBlockHashes'];groups=response['chainBlockAcceptedTransactions']
  c.require(len(set(added))==len(added) and len(set(removed))==len(removed) and len(added)==len(groups),'duplicate/incomplete chain delta')
  if removed:
   c.require(set(removed)<=set(chain),'removed unavailable checkpoint history');first=min(chain.index(h) for h in removed);c.require(set(chain[first:])==set(removed),'noncontiguous removal');chain=chain[:first]
   for h in removed:generation.pop(h)
   cursor=chain[-1] if chain else checkpoint['cursor']
  c.require(not set(added)&set(generation),'replayed active accepting group')
  for h,g in zip(added,groups):
   c.unhex(h,32);c.require(g['chainBlockHeader']['hash']==h and isinstance(g['acceptedTransactions'],list),'accepting group/header mismatch')
   generation[h]=page_seq
   for ref in refs:
    if ref['page_seq']==page_seq and ref['accepting_hash']==h:
     pos=ref['transaction_position'];c.require(type(pos) is int and 0<=pos<len(g['acceptedTransactions']),'index transaction position')
     tx=g['acceptedTransactions'][pos];c.require(hashlib.sha256(canonical(tx)).hexdigest()==ref['body_sha256'],'index retained body SHA mismatch')
     c.require(tx['verboseData']['transactionId']==ref['txid'] and tx['verboseData']['hash']==ref['full_hash'],'index body/id/fullhash mismatch')
     c.require(ref['txid'] not in found,'duplicate candidate evidence');found[ref['txid']]=tx;found_headers[ref['txid']]=g['chainBlockHeader']
  chain.extend(added)
  if added:cursor=added[-1]
  c.require(added or removed or cursor==commit['cursor'],'no progress before frozen horizon')
 c.require(page_seq==commit['seq'] and cursor==commit['cursor'],'incomplete capture range')
 for ref in refs:c.require(generation.get(ref['accepting_hash'])==ref['page_seq'] and ref['txid'] in found,'stale removed/readded or missing indexed acceptance')
 c.require(chain.index(funding['accepting_hash'])<chain.index(spender['accepting_hash']) or (funding['accepting_hash']==spender['accepting_hash'] and funding['transaction_position']<spender['transaction_position']),'lineage acceptance ordering')
 emit('underlying-evidence-verified',{'seconds':time.monotonic()-start,'pages':page_seq-checkpoint['seq']})
 verified_context=None
 if getattr(native,'requires_verified_funding_context',False):
  header=found_headers[funding['txid']];score=r.rpc_uint(header['daaScore'])
  tx=found[funding['txid']]
  c.require(tx['subnetworkId']=='00'*20 and bool(tx['inputs']),'ordinary noncoinbase funding required')
  verified_context={'outpoint':hint['S0_outpoint'],'block_daa_score':score,'accepting_hash':funding['accepting_hash'],'accepting_page_seq':funding['page_seq'],'run_id':run_id,'checkpoint':checkpoint,'commit':commit}
 callbacks=0
 def counted(tx,context):
  nonlocal callbacks
  callbacks+=1
  if context is not None and verified_context is not None:
   c.require(context['state']=='s0' and list(context['outpoint'])==verified_context['outpoint'],'historical context outside verified S0')
   context=dict(context,verified_funding_context=verified_context)
  return native(tx,context)
 scan=r.Scanner(locator,bundle,counted,inventory);scan.transitions=[];seen={}
 # All existing relevant native proof, witness, output and conservation checks.
 scan._apply_body(found[funding['txid']],seen)
 c.require(scan.funding_authenticated,'S0 funding body not authenticated')
 scan._apply_body(found[spender['txid']],seen)
 c.require(scan.state=='s1' and len(scan.transitions)==1,'expected exact S0->S1 lineage not found')
 scan.cursor=commit['cursor']
 emit('S1-first-discovered',{'native_callbacks':callbacks,'underlying_funding_and_continuation_verified':True})
 return scan,callbacks

def from_chunks(directory,locator,bundle,inventory,native,hint,checkpoint,commit,run_id,manifest_hash,emit=lambda *args:None):
 return discover(iter_pages(directory,checkpoint,run_id,commit,manifest_hash),locator,bundle,inventory,native,hint,checkpoint,commit,run_id,emit)
