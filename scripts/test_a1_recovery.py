#!/usr/bin/env python3
"""Scanner adversaries using explicitly synthetic archive/body validation.

These tests exercise scanner semantics only; dummy proof bytes and callback do
not constitute Full validation, live accepted history or G5 machine-loss success.
"""
import copy
import hashlib
import unittest
import a1_check as c
import a1_recovery as r
from test_a1_check import TERMS, RECIPIENT, SECRET, COMMITMENT, INSTANCE


def push(b):
 if not b:return b'\0'
 if len(b)==1 and 1<=b[0]<=16:return bytes((0x50+b[0],))
 if len(b)<=75:return bytes((len(b),))+b
 if len(b)<256:return b'\x4c'+bytes((len(b),))+b
 return b'\x4d'+len(b).to_bytes(2,'little')+b


def fixtures():
 d0=b'synthetic-d0';d1=b'synthetic-d1';spk0=c.p2sh(d0);spk1=c.p2sh(d1);q=TERMS.checked()
 b={'network':'testnet-10','genesis_hex':c.GENESIS.hex(),'instance_hex':INSTANCE.hex(),'claim_commitment_hex':COMMITMENT.hex(),'recipient':{'spk_hex':RECIPIENT.hex()},'states':{'s0':{'R':str(q['R0']),'spk_hex':spk0.hex()},'s1':{'R':str(q['R1']),'spk_hex':spk1.hex()}},'branches':{}}
 for name,pair in zip(c.BRANCHES,((0,0),(0,1),(1,1))):
  values,outs=c.branch_values(*pair,TERMS,RECIPIENT,spk1)
  b['branches'][name]={'fee':str(values[3]),'outputs':[{'value':str(v),'spk_hex':s.hex(),'covenant':None} for v,s in outs]}
 locator={'network':'testnet-10','genesis_hex':c.GENESIS.hex(),'instance_hex':INSTANCE.hex(),'s0_txid_hex':'42'*32,'s0_index':'7','s0_amount':str(q['R0']),'s0_spk_hex':spk0.hex(),'s0_covenant':None,'scan_start_hash':'01'*32,'scan_start_blue_score':'1','scan_start_daa_score':'2','artifact_index_sha256':'ab'*32}
 return b,locator,d0,d1


def body(bundle,previous,branch,redeem,ident):
 outputs=[]
 for expected in bundle['branches'][branch]['outputs']:
  spk=bytes.fromhex(expected['spk_hex'])
  outputs.append({'value':int(expected['value']),'scriptPublicKey':spk.hex(),'covenant':None})
 selector=b'\0' if branch=='s0_continue' else b'\1'
 script=b''.join(map(push,[bytes(32),bytes(32),bytes(128),selector,redeem]))
 tx={'version':1,'inputs':[{'previousOutpoint':{'transactionId':previous[0],'index':previous[1]},'signatureScript':script.hex(),'sequence':2**64-1,'computeBudget':1700}],'outputs':outputs,'lockTime':0,'subnetworkId':'00'*20,'gas':0,'payload':'','storageMass':0,'verboseData':{'transactionId':ident}}
 tx['verboseData']['hash']=r.full_hash(tx)
 return tx


def page(start,added,transactions=None,removed=None):
 return {'startHash':start,'response':{'removedChainBlockHashes':removed or [],'addedChainBlockHashes':added,'chainBlockAcceptedTransactions':[{'chainBlockHeader':{'hash':h},'acceptedTransactions':ts} for h,ts in zip(added,transactions or [[] for _ in added])]}}


def fake_native(tx,context):
 return {'txid':tx['verboseData']['transactionId'],'full_hash':r.full_hash(tx),'full_valid':context is not None}


class RecoveryScannerTests(unittest.TestCase):
 def setUp(self):
  self.b,self.loc,self.d0,self.d1=fixtures();self.scan=r.Scanner(self.loc,self.b,fake_native,'ab'*32)
  self.cont=body(self.b,('42'*32,7),'s0_continue',self.d0,'43'*32)
  self.exit=body(self.b,('43'*32,0),'s1_terminal',self.d1,'44'*32)
 def first(self):return page('01'*32,['02'*32],[[self.cont]])
 def utxo(self,state='s1'):
  return {'transaction_id':'43'*32 if state=='s1' else '42'*32,'index':'0' if state=='s1' else '7','value':self.b['states'][state]['R'],'spk_hex':self.b['states'][state]['spk_hex'],'covenant':None}

 def test_old_locator_discovers_successor_over_two_pages(self):
  self.scan.page(page('01'*32,['02'*32],[[]]),'03'*32)
  result=self.scan.page(page('02'*32,['03'*32],[[self.cont]]),'03'*32)
  self.assertEqual(result['current_outpoint'],('43'*32,0));self.assertEqual(result['paid'],'400000000')
  self.assertTrue(self.scan.reconcile_utxos([self.utxo()],'03'*32)['current_utxo_reconciled'])
  self.assertFalse(result['terminal_spendability_demonstrated']);self.assertFalse(result['live_tn10_demonstrated'])

 def test_fresh_terminal_history_and_direct_exit_accounting(self):
  self.scan.page(self.first(),'03'*32)
  result=self.scan.page(page('02'*32,['03'*32],[[self.exit]]),'03'*32)
  self.assertEqual((result['state'],result['paid'],result['fees']),('terminal','1020000000','40000000'))
  self.scan.reconcile_utxos([],'03'*32)
  direct=body(self.b,('42'*32,7),'s0_terminal',self.d0,'45'*32)
  scan=r.Scanner(self.loc,self.b,fake_native,'ab'*32);result=scan.page(page('01'*32,['02'*32],[[direct]]),'02'*32)
  self.assertEqual((result['state'],result['paid'],result['fees']),('terminal','1040000000','20000000'))

 def test_reorg_rolls_back_credit_and_pointer_before_replay(self):
  self.scan.page(self.first(),'02'*32)
  direct=body(self.b,('42'*32,7),'s0_terminal',self.d0,'45'*32)
  result=self.scan.page(page('02'*32,['04'*32],[[direct]],['02'*32]),'04'*32)
  self.assertEqual((result['state'],result['paid']),('terminal','1040000000'));self.assertEqual(len(result['transitions']),1)

 def test_missing_reordered_duplicate_pruned_pages_fail_atomically(self):
  bad=[page('ff'*32,['02'*32],[[self.cont]]),page('01'*32,[]),page('01'*32,['02'*32,'02'*32],[[self.cont],[]])]
  missing=self.first();missing['response']['chainBlockAcceptedTransactions']=[];bad.append(missing)
  reordered=page('01'*32,['02'*32,'03'*32],[[self.cont],[]]);reordered['response']['chainBlockAcceptedTransactions'].reverse();bad.append(reordered)
  bad.append(page('01'*32,[],removed=['99'*32]))
  for p in bad:
   with self.subTest(p=p),self.assertRaises(c.Invalid):self.scan.page(p,'03'*32)
   self.assertEqual((self.scan.cursor,self.scan.state,self.scan.paid),('01'*32,'s0',0))

 def test_poisoned_history_wrong_output_wrong_proof_callback_fail(self):
  mutations=[]
  x=copy.deepcopy(self.cont);x['inputs'][0]['signatureScript']='00';mutations.append(x)
  x=copy.deepcopy(self.cont);x['outputs'].reverse();mutations.append(x)
  x=copy.deepcopy(self.cont);x['outputs'][0]['value']+=1;mutations.append(x)
  x=copy.deepcopy(self.cont);x['outputs'][0]['covenant']={'authorizingInput':0,'covenantId':'00'*32};mutations.append(x)
  for tx in mutations:
   tx['verboseData']['hash']=r.full_hash(tx)
   with self.assertRaises(c.Invalid):self.scan.page(page('01'*32,['02'*32],[[tx]]),'02'*32)
  poisoned=copy.deepcopy(self.cont);poisoned['verboseData']['hash']='00'*32
  with self.assertRaises(c.Invalid):self.scan.page(page('01'*32,['02'*32],[[poisoned]]),'02'*32)
  scan=r.Scanner(self.loc,self.b,lambda tx,cx:{'txid':tx['verboseData']['transactionId'],'full_hash':r.full_hash(tx),'full_valid':False},'ab'*32)
  with self.assertRaises(c.Invalid):scan.page(self.first(),'02'*32)

 def test_conflict_stale_locator_missing_or_duplicate_utxo(self):
  conflict=body(self.b,('42'*32,7),'s0_terminal',self.d0,'45'*32)
  with self.assertRaises(c.Invalid):self.scan.page(page('01'*32,['02'*32],[[self.cont,conflict]]),'02'*32)
  loc=copy.deepcopy(self.loc);loc['s0_amount']='1'
  with self.assertRaises(c.Invalid):r.Scanner(loc,self.b,fake_native,'ab'*32)
  self.scan.page(self.first(),'02'*32)
  for observed in ([],[self.utxo(),self.utxo()],[self.utxo(),self.utxo('s0')]):
   with self.assertRaises(c.Invalid):self.scan.reconcile_utxos(observed,'02'*32)

 def test_private_backup_and_wrong_secret(self):
  self.assertTrue(r.check_private_backup(self.b,SECRET,RECIPIENT[3:35])['claim_secret_matches'])
  with self.assertRaises(c.Invalid):r.check_private_backup(self.b,bytes(32),RECIPIENT[3:35])
  with self.assertRaises(c.Invalid):r.check_private_backup(self.b,SECRET,bytes(32))

 def test_push_encodings_permit_byte_equivalence_reject_nonpush(self):
  for script in ('0100','4c0100','4d010000'):self.assertEqual(r.pushes(bytes.fromhex(script)),[b'\0'])
  for script in ('51','0101','4c0101','4d010001'):self.assertEqual(r.pushes(bytes.fromhex(script)),[b'\1'])
  for script in ('76','4c','4d01','4e010000','0200'):
   with self.assertRaises(c.Invalid):r.pushes(bytes.fromhex(script))

 def test_full_archive_can_include_native_v0_coinbase_bodies(self):
  # Upstream consensus hashing/tx.rs literal empty-v0 vector, independent hash.
  tx={'version':0,'inputs':[],'outputs':[],'lockTime':0,'subnetworkId':'00'*20,'gas':0,'payload':'','mass':0,'verboseData':{'transactionId':'2c18d5e59ca8fc4c23d9560da3bf738a8f40935c11c162017fbf2c907b7e665c','hash':'c9e29784564c269ce2faaffd3487cb4684383018ace11133de082dce4bb88b0b'}}
  self.assertEqual(r.full_hash(tx),tx['verboseData']['hash'])
  result=self.scan.page(page('01'*32,['02'*32],[[tx,self.cont]]),'02'*32)
  self.assertEqual(result['state'],'s1')


if __name__=='__main__':unittest.main()
