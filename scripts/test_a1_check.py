#!/usr/bin/env python3
"""Independent fixture literals from ADR-0003; expectations never use Rust."""
import hashlib
import struct
import unittest
import tempfile
from pathlib import Path
import json
import a1_check as c

RECIPIENT = bytes.fromhex('00002079be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ac')
SUCCESSOR = bytes.fromhex('0000aa20'+'aa'*32+'87')
SECRET = bytes(range(32, 64))
INSTANCE = bytes(range(32))
COMMITMENT = bytes.fromhex('72dbb7336c76780023f83da4c355f2eeea85733b13d3477697917790c1229084')
TXID = bytes(range(64, 96))
TERMS = c.Terms(1_000_000_000,60_000_000,400_000_000,20_000_000,20_000_000,20_000_000)
GOLDEN = [
 ('0af7df62cf63215e4c4388f114c3582a737996978c2b976451205664a0fe6ed5','a552c701f0f1a1c25622cb95ea966c8c4331dae1d419f006d37bac1a4e5894df',276),
 ('37dfc0262dfc6ba7c9cbade0539b8c1337cb1fe7f5412874ecb6e2752f2ff3e2','7b9be40d74dd86c8165f3e860192e3825d3375777ecc4cc44d1e78402a45a4b4',226),
 ('4ed80e53e56a98bdbd2f6a4b039b6dbaedd054351258a47c4b9a2fb4d26c1583','419ab03e0da84cdd65519e5fc02d1492f49655ef44adb01bf9dbf03853e5d91e',226)]


def schema_fixture(root):
 """Opaque dummy-key/small-matrix schema fixture, never a proof qualification."""
 root=Path(root);(root/'reference').mkdir()
 def save(path,data,r1cs=False):
  (root/path).write_bytes(data)
  return {'path':path,'bytes':str(len(data)),'sha256':c.sha(data)}|({'format':'KPI-A1/R1CS/v1'} if r1cs else {})
 keys={n:bytes(224)+(6).to_bytes(8,'little')+bytes((i+1,))*192 for i,n in enumerate(c.BRANCHES)}
 q=TERMS.checked();env=bytes.fromhex('b2519db614'+'00'*20+'88b7009dc4009db5009d74549d')
 d1=env+b'\x51\x88'+c.expected_body(q['R1'],[(q['P1'],RECIPIENT)],keys['s1_terminal'])
 spk1=c.p2sh(d1);scripts=c.expected_scripts(TERMS,RECIPIENT,spk1,keys)
 pins={'kpi_source_commit':'12'*20,'rusty_kaspa_commit':'01b532e8b553523216471682649693af92f0fd16','rust_toolchain':'1.91.0','target':'x86_64-unknown-linux-gnu','cargo_lock_sha256':'13'*32,'dependency_versions':{'ark-bn254':'0.6.0','sha2':'0.10.9'},'sdk_archive_sha256':'ba674e109ff5dd8bedc4dc2ee8a5ecdf4b600b1178a541d77888ec58310b6124','node_archive_sha256':'5ba61c05c013a4856491a8a17666fa73f7bd2aecbfed8affe8ffdc077361dad8','build_commands':['cargo build --locked --release'],'checker_source_commit':'14'*20}
 intent={'schema':'kpi-a1-intent/v1','scope':'local-unfunded-fixture','genesis_hex':c.GENESIS.hex(),'instance_hex':INSTANCE.hex(),'claim_commitment_hex':COMMITMENT.hex(),'recipient_spk_hex':RECIPIENT.hex(),'terms':dict(zip(('l0','b0','w','f0','fc','f1'),map(str,(TERMS.L0,TERMS.B0,TERMS.W,TERMS.f0,TERMS.fc,TERMS.f1)))),'pins':pins}
 manifest={'schema':'kpi-a1-artifacts/v1','protocol':'KPI-A1/TN10/finite/v1','network':'testnet-10','genesis_hex':c.GENESIS.hex(),'instance_hex':INSTANCE.hex(),'claim_commitment_hex':COMMITMENT.hex(),'recipient':{'address':c.address_for_spk(RECIPIENT),'spk_version':'0','spk_hex':RECIPIENT.hex()},'states':{},'branches':{},'abi':{'verifier_tag_hex':'20','public_inputs':c.PUBLIC,'scalar_bytes':'32','proof_bytes':'128','vk_bytes':'424','witness_order':['tag_hi','tag_lo','proof','selector','redeem']},'envelope':{'tx_version':'1','subnetwork_hex':'00'*20,'gas':'0','payload_hex':'','lock_time':'0','sequence_policy':'relative-lock-disabled','compute_budgets':dict.fromkeys(c.BRANCHES,'1700')},'pins':pins,'inspection':{},'recovery':{'source_id':'synthetic-independent-archive','network_genesis_hex':c.GENESIS.hex(),'retention_start_hash':'15'*32,'retention_policy':'synthetic-full-range','locator_schema':'kpi-a1-locator/v1','private_backup_items':['claim-secret','recipient-key'],'public_artifact_items':['all-artifacts']}}
 for stage in (0,1):
  name='s'+str(stage)
  manifest['states'][name]={'stage':str(stage),'R':str(q['R'+str(stage)]),'L':str(q['L'+str(stage)]),'B':str(q['B'+str(stage)]),'redeem':save(name+'.redeem',scripts[name]),'spk_hex':c.p2sh(scripts[name]).hex()}
 matrix=b'KPI-A1/R1CS/v1\0'+struct.pack('<IQQ',5,6,1)+bytes(24)
 receipts={}
 for name,pair in zip(c.BRANCHES,((0,0),(0,1),(1,1))):
  values,outputs=c.branch_values(*pair,TERMS,RECIPIENT,spk1)
  context=c.encode_context(*pair,c.GENESIS,INSTANCE,COMMITMENT,TERMS,RECIPIENT,spk1)
  pk=keys[name]+bytes(100)
  manifest['branches'][name]={'stage':str(pair[0]),'mode':str(pair[1]),'selector_hex':'00' if pair[1]==0 else '01','fee':str(values[3]),'next_R':str(values[4]),'next_L':str(values[5]),'next_B':str(values[6]),'outputs':[{'index':str(i),'value':str(v),'spk_hex':spk.hex(),'covenant':None} for i,(v,spk) in enumerate(outputs)],'context_hex':context.hex(),'context_sha256':c.sha(context),'relation_id':'sha256-preimage-and-outpoint-tag/v1','r1cs':save(name+'.r1cs',matrix,True),'pk':save(name+'.pk',pk),'vk':save(name+'.vk',keys[name])}
  (root/'reference'/(name+'.r1cs')).write_bytes(matrix)
  receipts[name]={'context_sha256':c.sha(context),'r1cs_sha256':c.sha(matrix),'pk_sha256':c.sha(pk),'vk_sha256':c.sha(keys[name])}
 receipt={'schema':'kpi-a1-setup-observation/v1','scope':'local-unfunded-fixture','observer':'synthetic-parser-test-only','build_pins':pins,'branches':receipts,'setup_randomness_retained':False}
 disassembly=c.canonical_json({name:c.disassemble(data) for name,data in scripts.items()})
 report=c.canonical_json(c.expected_report(dict.fromkeys(c.BRANCHES,c.parse_r1cs(matrix)),scripts))
 (root/'disassembly.json').write_bytes(disassembly);(root/'independent-checker-report.json').write_bytes(report)
 manifest['inspection']={'normalized_r1cs_sha256':dict.fromkeys(c.BRANCHES,c.sha(matrix)),'script_disassembly_sha256':c.sha(disassembly),'checker_report_sha256':c.sha(report),'setup_observation_receipt_sha256':c.sha(c.canonical_json(receipt))}
 (root/'manifest.json').write_text(json.dumps(manifest))
 return manifest,intent,receipt


class IndependentCodecTests(unittest.TestCase):
 def context(self,stage=0,mode=0):
  return c.encode_context(stage,mode,c.GENESIS,INSTANCE,COMMITMENT,TERMS,RECIPIENT,SUCCESSOR)

 def test_all_golden_branches_and_abi(self):
  self.assertEqual(hashlib.sha256(SECRET).digest(),COMMITMENT)
  for pair,golden in zip(((0,0),(0,1),(1,1)),GOLDEN):
   b=self.context(*pair); t=c.tag(b,SECRET,TXID,7)
   self.assertEqual((c.sha(b),t.hex(),len(b)),golden)
   parsed=c.parse_context(b)
   self.assertEqual((parsed['stage'],parsed['mode']),pair)
   inputs=c.public_inputs(TXID,7,t)
   self.assertEqual([len(x) for x in inputs],[32]*5)
   self.assertEqual(inputs[0],bytes(range(64,80))+bytes(16))
   self.assertEqual(inputs[2],bytes.fromhex('07000000')+bytes(28))

 def test_accounting_exact_rebate(self):
  self.assertEqual(TERMS.checked(),{'R0':1060000000,'L0':1000000000,'B0':60000000,'L1':600000000,'B1':40000000,'R1':640000000,'P0':1040000000,'P1':620000000})

 def test_boundary_rejections(self):
  for args in [(0,5,1,1,1,1),(10,5,0,1,1,1),(10,5,10,1,1,1),(10,5,11,1,1,1),(10,5,1,6,1,1),(10,5,1,1,5,1),(10,5,1,1,0,1),(c.MAX_SOMPI,5,1,1,1,1),(2**64-1,5,1,1,1,1),(-1,5,1,1,1,1),(True,5,1,1,1,1)]:
   with self.subTest(args=args),self.assertRaises(c.Invalid): c.Terms(*args).checked()
  for pair in ((1,0),(0,2),(2,1),(-1,0)):
   with self.subTest(pair=pair),self.assertRaises(c.Invalid): self.context(*pair)
  c.Terms(c.MAX_SOMPI-5,5,1,1,1,1).checked()

 def test_negative_tags_literal_oracle(self):
  for offset,value,expected in [(87,2,'ebe7a11139890da093c561b8eacb29aa5afcbc8a64a0845fa6bddc39f0280b84'),(86,1,'05299d3cbc51595cca3b85309546a7382598ff058f43c1120c19daaf68fa8640'),(190,1,'0fab892f5af61ff60b33adc119772d9d3b279952386d1c306088d7d340673c8d'),(226,1,'910bfe668bef282e6aaa02064e1d2c81de1882e0c9a22e2a13b19e8026c8b11a'),(242,0x78,'729a917d85a7946600734e1ea684b695f27ce754f12f3b712c9a8cc14bac9557')]:
   b=bytearray(self.context());b[offset]=value
   self.assertEqual(c.tag(bytes(b),SECRET,TXID,7).hex(),expected)

 def test_malformed_contexts(self):
  b=self.context()
  negatives=[b+b'\0',b[:-1]]
  for offset,replacement in [(87,b'\x02'),(86,b'\x01'),(190,b'\x01'),(226,b'\x01'),(185,bytes.fromhex('24000000')),(176,b'\x01')]:
   negatives.append(b[:offset]+replacement+b[offset+len(replacement):])
  for bad in negatives:
   with self.subTest(bad=bad.hex()),self.assertRaises(c.Invalid): c.parse_context(bad)

 def test_strict_number_and_hex(self):
  for bad in ('01','-1','+1',' 1','1.0',1,True):
   with self.subTest(bad=bad),self.assertRaises(c.Invalid): c.decimal(bad)
  for bad in ('0x01','FF','f',' 00'):
   with self.subTest(bad=bad),self.assertRaises(c.Invalid): c.unhex(bad)

 def test_r1cs_independent_parser_and_evaluator(self):
  def term(index,n):return struct.pack('<Q',index)+n.to_bytes(32,'little')
  def row(*terms):return struct.pack('<Q',len(terms))+b''.join(terms)
  # x1 * 1 = x2; all public variables still allocated in this parser fixture.
  prefix=b'KPI-A1/R1CS/v1\0'+struct.pack('<IQQ',5,6,1)
  matrix=prefix+row(term(1,1))+row(term(0,1))+row(term(2,1))
  self.assertEqual(c.parse_r1cs(matrix,[1,7,7,0,0,0])['constraint_count'],1)
  with self.assertRaises(c.Invalid):c.parse_r1cs(matrix,[1,7,8,0,0,0])
  for changed in (matrix+b'\0',matrix[:-1],prefix+row(term(1,c.FR))+row()+row(),prefix+row(term(1,1),term(1,2))+row()+row(),prefix+row(term(6,1))+row()+row(),prefix+row(term(1,0))+row()+row()):
   with self.assertRaises(c.Invalid):c.parse_r1cs(changed)

 def test_duplicate_json_unknown_float_and_escaping_artifact(self):
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'x.json'
   for text in ('{"R":"1","R":"2"}','{"R":1.5}','{"R":NaN}'):
    path.write_text(text)
    with self.assertRaises(c.Invalid):c.load_json(path)
   path.write_bytes(b'abc')
   descriptor={'path':'x.json','bytes':'3','sha256':c.sha(b'abc')}
   self.assertEqual(c.artifact(td,descriptor),b'abc')
   for name in ('../x.json','/tmp/x.json','a/../x.json','./x.json','missing'):
    with self.assertRaises(c.Invalid):c.artifact(td,descriptor|{'path':name})
   for mutation in ({'bytes':'4'},{'sha256':'00'*32},{'extra':'x'}):
    with self.assertRaises(c.Invalid):c.artifact(td,descriptor|mutation)

 def test_exact_script_independent_construction(self):
  # Explicit opaque keys: script reconstruction test only, no valid key/proof.
  vk=bytes(424)
  q=TERMS.checked()
  envelope=bytes.fromhex('b2519db614'+'00'*20+'88b7009dc4009db5009d74549d')
  d1=envelope+c.script_push(b'\1')+b'\x88'+c.expected_body(q['R1'],[(q['P1'],RECIPIENT)],vk)
  scripts=c.expected_scripts(TERMS,RECIPIENT,c.p2sh(d1),dict.fromkeys(c.BRANCHES,vk))
  self.assertEqual(scripts['s1'],d1)
  self.assertEqual(scripts['s0'].count(bytes.fromhex('4da801')+vk+bytes.fromhex('0120a6')),2)
  self.assertEqual(scripts['s1'].count(bytes.fromhex('4da801')+vk+bytes.fromhex('0120a6')),1)
  self.assertTrue(scripts['s0'].startswith(envelope+bytes.fromhex('760100876375')))
  self.assertTrue(scripts['s0'].endswith(b'\x68'))
  with self.assertRaises(c.Invalid):c.expected_scripts(TERMS,RECIPIENT,SUCCESSOR,dict.fromkeys(c.BRANCHES,vk))

 def test_strict_bundle_mutations_and_owner_intent(self):
  import copy
  with tempfile.TemporaryDirectory() as td:
   manifest,intent,receipt=schema_fixture(td)
   def check(m,own=intent,rec=receipt):
    (Path(td)/'manifest.json').write_text(json.dumps(m))
    return c.check_bundle(td,own,Path(td)/'reference',rec,lambda pk,vk:True)
   # Dummy callback only tests schema/checker control flow, not key qualification.
   self.assertTrue(check(manifest)['parameter_consistency'])
   for mutator in (lambda m:m.update(extra='x'),lambda m:m['states']['s1'].update(R='1'),lambda m:m['branches']['s0_continue'].update(fee='1'),lambda m:m['branches']['s1_terminal'].update(mode='0'),lambda m:m['branches']['s0_terminal'].update(selector_hex='02'),lambda m:m['branches']['s0_continue']['outputs'].reverse(),lambda m:m['abi']['public_inputs'].reverse(),lambda m:m['envelope'].update(tx_version='2'),lambda m:m['pins'].update(rust_toolchain='1.90.0')):
    changed=copy.deepcopy(manifest);mutator(changed)
    with self.assertRaises(c.Invalid):check(changed)
   wrong=copy.deepcopy(intent);wrong['terms']['l0']='1000000001'
   with self.assertRaises(c.Invalid):check(manifest,wrong)
   wrong=copy.deepcopy(receipt);wrong['setup_randomness_retained']=True
   with self.assertRaises(c.Invalid):check(manifest,rec=wrong)
   path=Path(td)/'s1_terminal.pk';original=path.read_bytes();path.write_bytes(original+b'\0')
   with self.assertRaises(c.Invalid):check(manifest)
   path.write_bytes(original);path.unlink()
   with self.assertRaises(c.Invalid):check(manifest)
   # Self-consistent replacement hashes cannot mask independently wrong matrix.
   path=Path(td)/'s0_continue.r1cs';changed=path.read_bytes()+b'\0';path.write_bytes(changed)
   modified=copy.deepcopy(manifest);modified['branches']['s0_continue']['r1cs'].update(bytes=str(len(changed)),sha256=c.sha(changed))
   with self.assertRaises(c.Invalid):check(modified)


if __name__=='__main__': unittest.main()
