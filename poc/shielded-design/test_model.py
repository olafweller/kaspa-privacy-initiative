"""Adversarial economic/role tests. Oracle-model checks are not ZK verification."""
import copy
import json
import random
import unittest
from nacl.exceptions import BadSignatureError
from model import MAX, NETWORK, POOL, Note, Pool, Proof, ProofOracle, Recipient, Wallet, amount, hash_id


class PaymentModelTests(unittest.TestCase):
    def setUp(self):
        self.alice, self.bob, self.mallory = [Wallet(n) for n in ['Alice', 'Bob', 'Mallory']]
        self.oracle = ProofOracle(); self.pool = Pool(self.oracle)
        self.note = self.alice.note(1_000_000_000, 'deposit')
        self.event = self.pool.funded_deposit('native-deposit-1', self.note, self.alice)
        self.credit = self.oracle.credit(self.event, self.note, self.alice.address)

    def funded(self):
        self.assertTrue(self.pool.process(self.credit)['accepted'])

    def transfer(self, fee=0):
        change = self.alice.note(600_000_000, 'change')
        received = self.bob.note(400_000_000-fee, 'receipt')
        p = self.oracle.spend(self.alice, [self.note], [(change, self.alice.address), (received, self.bob.address)],
                              list(self.pool.commitments), fee=fee)
        return p, change, received

    def economic(self):
        return copy.deepcopy({k:v for k,v in self.pool.__dict__.items() if k not in ['verifier','outcomes']})

    def test_complete_alice_bob_cycle_and_change(self):
        stages = [self.pool.invariant()]; self.funded(); stages.append(self.pool.invariant())
        proof, change, received = self.transfer(); self.assertTrue(self.pool.process(proof)['accepted'])
        found = self.bob.discover(self.pool.outputs)
        self.assertEqual(found, [received]); self.assertIn(change, self.alice.discover(self.pool.outputs))
        stages.append(self.pool.invariant())
        withdraw = self.oracle.spend(self.bob, found, [], list(self.pool.commitments),
                                      withdrawal={'recipient': 'bob-native-p2pk', 'amount': received.value})
        self.pool.fund_rent(50_000_000)
        result = self.pool.process(withdraw); self.assertTrue(result['accepted']); stages.append(self.pool.invariant())
        self.assertEqual(self.pool.payout(result['id'], 'bob-native-p2pk', 400_000_000, 50_000_000, 600_000_000),450_000_000)
        stages.append(self.pool.invariant())
        self.assertEqual([(s['reserve'],s['private'],s['unpaidExits']) for s in stages],
                         [(1_000_000_000,0,0),(1_000_000_000,1_000_000_000,0),
                          (1_000_000_000,1_000_000_000,0),(1_000_000_000,600_000_000,400_000_000),
                          (600_000_000,600_000_000,0)])

    def test_duplicate_spends_same_and_later_batch_are_atomic(self):
        self.funded(); first,_,_ = self.transfer()
        a=self.alice.note(500_000_000,'alternative-a');b=self.bob.note(500_000_000,'alternative-b')
        second=self.oracle.spend(self.alice,[self.note],[(a,self.alice.address),(b,self.bob.address)],list(self.pool.commitments))
        self.assertTrue(self.pool.process(first)['accepted']); before=self.economic()
        self.assertFalse(self.pool.process(second)['accepted']); self.assertEqual(before,self.economic())
        self.assertFalse(self.pool.process(second)['accepted']); self.assertEqual(before,self.economic())
        self.assertEqual(len(self.pool.outcomes),4)  # Includes credit and both rejected lane operations.

    def test_duplicate_input_within_one_operation(self):
        self.funded()
        with self.assertRaisesRegex(ValueError,'duplicate'):
            self.oracle.spend(self.alice,[self.note,self.note],[],list(self.pool.commitments))

    def test_invalid_proof_then_valid_operation_continues(self):
        self.funded(); good,_,_=self.transfer(); bad=copy.deepcopy(good);bad.token='forged'
        before=self.economic();self.assertFalse(self.pool.process(bad)['accepted']);self.assertEqual(before,self.economic())
        self.assertTrue(self.pool.process(good)['accepted'])

    def test_host_cannot_misclassify_valid_operation(self):
        self.funded();good,_,_=self.transfer();self.assertTrue(self.pool.process(good,host_claim='reject')['accepted'])

    def test_unauthorized_and_view_only_spending(self):
        self.funded()
        with self.assertRaisesRegex(ValueError,'unauthorized'):
            self.oracle.spend(self.mallory,[self.note],[],list(self.pool.commitments))
        reader=copy.copy(self.alice);reader._spend=self.mallory._spend
        self.assertEqual(reader.discover(self.pool.outputs),[self.note])
        with self.assertRaises(BadSignatureError):
            self.oracle.spend(reader,[self.note],[(self.bob.note(1_000_000_000,'out'),self.bob.address)],list(self.pool.commitments))

    def test_inflation_and_range_errors(self):
        self.funded()
        with self.assertRaisesRegex(ValueError,'conservation'):
            self.oracle.spend(self.alice,[self.note],[(self.bob.note(1_000_000_001,'inflated'),self.bob.address)],list(self.pool.commitments))
        for bad in [-1, MAX+1, True, 1.0, '10']:
            with self.subTest(value=bad),self.assertRaises(ValueError): amount(bad)
        with self.assertRaises(ValueError): self.alice.note(0,'zero')

    def test_native_reserve_overflow_changes_nothing(self):
        p=Pool(self.oracle);n=self.alice.note(MAX,'large');p.funded_deposit('large',n,self.alice)
        before=p.invariant()
        with self.assertRaises(ValueError):p.funded_deposit('extra',self.alice.note(1,'extra'),self.alice)
        self.assertEqual(p.invariant(),before);self.assertNotIn('extra',p.deposits)

    def test_wrong_anchor_and_membership(self):
        self.funded()
        with self.assertRaisesRegex(ValueError,'membership'):
            self.oracle.spend(self.alice,[self.note],[(self.bob.note(1_000_000_000,'other'),self.bob.address)],[])
        good,_,_=self.transfer();body=copy.deepcopy(good.public);body['anchor']='unknown'
        p=self.oracle._register(body)  # Model a cryptographically valid statement for an unallowed root.
        before=self.economic();self.assertFalse(self.pool.process(p)['accepted']);self.assertEqual(before,self.economic())

    def test_old_membership_root_remains_usable_with_current_nullifiers(self):
        self.funded();old=list(self.pool.commitments)
        other=self.bob.note(100,'independent');event=self.pool.funded_deposit('second',other,self.bob)
        self.pool.process(self.oracle.credit(event,other,self.bob.address))
        p=self.oracle.spend(self.alice,[self.note],[(self.bob.note(1_000_000_000,'old-root-output'),self.bob.address)],old)
        self.assertTrue(self.pool.process(p)['accepted'])

    def test_network_pool_version_boundaries(self):
        self.funded();good,_,_=self.transfer()
        for key,value in [('network','mainnet'),('pool','another-pool'),('version',2),('version',True),('version',1.0)]:
            body=copy.deepcopy(good.public);body[key]=value;body['nullifiers']=[hash_id([value,n]) for n in body['nullifiers']]
            before=self.economic();self.assertFalse(self.pool.process(self.oracle._register(body))['accepted']);self.assertEqual(before,self.economic())
        self.assertTrue(self.pool.process(good)['accepted'])
        self.assertFalse(self.pool.process(good)['accepted'])

    def test_output_payout_and_ciphertext_substitution_breaks_statement(self):
        self.funded();good,_,_=self.transfer()
        for mutation in ['output','recipient','ciphertext']:
            bad=copy.deepcopy(good)
            if mutation=='output':bad.public['outputs'][0]['commitment']='forged'
            elif mutation=='recipient':bad.public['withdrawal']['recipient']='mallory'
            else:bad.public['outputs'][0]['ciphertext']='00'
            before=self.economic();self.assertFalse(self.pool.process(bad)['accepted']);self.assertEqual(before,self.economic())

    def test_recipient_detects_corrupt_or_unavailable_delivery(self):
        self.funded();proof,_,note=self.transfer();self.pool.process(proof)
        self.assertEqual(self.bob.discover(self.pool.outputs),[note])
        wrong=copy.deepcopy(self.pool.outputs);wrong[-1]['ciphertext']='00'
        self.assertEqual(self.bob.discover(wrong),[]);self.assertEqual(self.bob.discover([]),[])
        wrong=copy.deepcopy(self.pool.outputs);wrong[-1]['commitment']='bad'
        self.assertEqual(self.bob.discover(wrong),[])
        # Missing delivery data is not successful recovery, even if the root survives.
        with self.assertRaises(ValueError): self.oracle.spend(self.bob,[],[],list(self.pool.commitments))

    def test_receive_address_key_substitution(self):
        note=self.bob.note(400_000_000,'receipt')
        forged=Recipient(self.bob.owner,self.mallory.address.incoming,self.bob.address.signature)
        with self.assertRaises(BadSignatureError):note.public(forged)

    def test_public_transfer_fields_do_not_include_input_note_or_secrets(self):
        self.funded();proof,_,_=self.transfer();blob=json.dumps(proof.public)
        for secret in [self.note.commitment,self.alice.owner,self.note.randomness,'merge_path','input_index']:
            self.assertNotIn(secret,blob)
        self.assertEqual(len(self.alice.note(1,'small').public(self.alice.address)['ciphertext']),
                         len(self.alice.note(MAX,'max').public(self.alice.address)['ciphertext']))

    def test_failed_credit_still_has_owner_recovery_or_retry(self):
        bad=copy.deepcopy(self.credit);bad.token='bad';self.assertFalse(self.pool.process(bad)['accepted'])
        self.assertEqual(self.pool.invariant()['pendingDeposits'],1_000_000_000)
        with self.assertRaises(BadSignatureError):self.pool.refund(self.event['id'],self.mallory.sign(['MODEL-REFUND',NETWORK,POOL,self.event['id']]))
        self.assertEqual(self.pool.deposits[self.event['id']]['state'],'pending')
        self.assertTrue(self.pool.process(self.credit)['accepted'])
        with self.assertRaises(ValueError):self.pool.refund(self.event['id'],self.alice.sign(['MODEL-REFUND',NETWORK,POOL,self.event['id']]))

    def test_owner_refund_then_credit_cannot_spend_same_deposit(self):
        sig=self.alice.sign(['MODEL-REFUND',NETWORK,POOL,self.event['id']])
        self.assertEqual(self.pool.refund(self.event['id'],sig),1_000_000_000)
        self.assertFalse(self.pool.process(self.credit)['accepted']);self.assertEqual(self.pool.reserve,0)
        with self.assertRaises(ValueError):self.pool.refund(self.event['id'],sig)
        with self.assertRaises(ValueError):self.pool.funded_deposit(self.event['id'],self.note,self.alice)

    def test_wrong_deposit_commitment_or_amount(self):
        with self.assertRaises(ValueError):self.oracle.credit(self.event,self.alice.note(2,'wrong'),self.alice.address)
        fake=copy.deepcopy(self.event);fake['id']='nonexistent'
        proof=self.oracle.credit(fake,self.note,self.alice.address)
        before=self.economic();self.assertFalse(self.pool.process(proof)['accepted']);self.assertEqual(before,self.economic())

    def withdraw(self):
        self.pool.fund_rent(50_000_000)
        self.funded();p=self.oracle.spend(self.alice,[self.note],[(self.alice.note(600_000_000,'change'),self.alice.address)],
                     list(self.pool.commitments),withdrawal={'recipient':'bob-native','amount':400_000_000})
        return self.pool.process(p)['id']

    def test_permission_rent_requires_explicit_external_funding(self):
        self.funded();p=self.oracle.spend(self.alice,[self.note],[],list(self.pool.commitments),
                     withdrawal={'recipient':'bob-native','amount':1_000_000_000})
        before=self.economic();self.assertFalse(self.pool.process(p)['accepted']);self.assertEqual(before,self.economic())
        self.pool.fund_rent(50_000_000);self.assertTrue(self.pool.process(p)['accepted'])

    def test_duplicate_output_commitments_reject_without_spending(self):
        self.funded();note=self.bob.note(500_000_000,'duplicate')
        p=self.oracle.spend(self.alice,[self.note],[(note,self.bob.address),(note,self.bob.address)],list(self.pool.commitments))
        before=self.economic();self.assertFalse(self.pool.process(p)['accepted']);self.assertEqual(before,self.economic())

    def test_native_payout_underpay_recipient_reserve_rent_and_replay(self):
        identity=self.withdraw()
        for params in [('mallory',400_000_000,50_000_000,600_000_000),('bob-native',399_999_999,50_000_000,600_000_000),
                       ('bob-native',400_000_000,50_000_000,599_999_999),('bob-native',400_000_000,49_999_999,600_000_000)]:
            before=self.economic()
            with self.assertRaises(ValueError):self.pool.payout(identity,*params)
            self.assertEqual(before,self.economic())
        self.pool.payout(identity,'bob-native',400_000_000,50_000_000,600_000_000)
        with self.assertRaises(ValueError):self.pool.payout(identity,'bob-native',400_000_000,50_000_000,200_000_000)

    def test_fee_claim_not_free_treasury_and_payout_bound(self):
        self.funded();p,_,_=self.transfer(fee=1000);out=self.pool.process(p);self.assertTrue(out['accepted'])
        self.assertEqual(self.pool.invariant()['unpaidFees'],1000);self.assertEqual(self.pool.reserve,1_000_000_000)
        with self.assertRaises(ValueError):self.pool.pay_fee(out['id'],'mallory',1000)
        with self.assertRaises(ValueError):self.pool.pay_fee(out['id'],'model-relayer',1001)
        self.pool.pay_fee(out['id'],'model-relayer',1000);self.assertEqual(self.pool.reserve,999_999_000)
        with self.assertRaises(ValueError):self.pool.pay_fee(out['id'],'model-relayer',1000)

    def test_payout_total_boundary_and_overflow_preserve_entire_state(self):
        rent = 50_000_000
        for principal in [MAX, MAX - rent + 1, MAX - rent]:
            with self.subTest(principal=principal):
                pool = Pool(self.oracle)
                note = self.alice.note(principal, 'payout-boundary')
                event = pool.funded_deposit('boundary-deposit', note, self.alice)
                self.assertTrue(pool.process(self.oracle.credit(event, note, self.alice.address))['accepted'])
                pool.fund_rent(rent)
                proof = self.oracle.spend(self.alice, [note], [], list(pool.commitments),
                                          withdrawal={'recipient': 'alice-native', 'amount': principal})
                result = pool.process(proof)
                self.assertTrue(result['accepted'])
                before = copy.deepcopy({k:v for k,v in pool.__dict__.items() if k != 'verifier'})
                if principal > MAX - rent:
                    with self.assertRaisesRegex(ValueError, 'integer sompi/range'):
                        pool.payout(result['id'], 'alice-native', principal, rent, 0)
                    self.assertEqual(before, {k:v for k,v in pool.__dict__.items() if k != 'verifier'})
                    pool.invariant()
                else:
                    self.assertEqual(pool.payout(result['id'], 'alice-native', principal, rent, 0), MAX)
                    self.assertTrue(pool.claims[result['id']]['paid'])
                    self.assertEqual((pool.reserve, pool.rent_reserve, pool.rent_paid), (0, 0, rent))
                    pool.invariant()

    def test_seeded_conservation_and_atomic_rejection_vectors(self):
        rng=random.Random(20261017)
        for n in range(64):
            pool=Pool(self.oracle);value=rng.randrange(1_000,10**12);fee=rng.randrange(0,value//4)
            note=self.alice.note(value,str(n));event=pool.funded_deposit(str(n),note,self.alice)
            pool.process(self.oracle.credit(event,note,self.alice.address))
            out=self.bob.note(value-fee,'p'+str(n));p=self.oracle.spend(self.alice,[note],[(out,self.bob.address)],list(pool.commitments),fee=fee)
            self.assertTrue(pool.process(p)['accepted']);before=pool.invariant()
            self.assertFalse(pool.process(p)['accepted']);self.assertEqual(before,pool.invariant())
            self.assertEqual(pool.private_total+sum(x['amount'] for x in pool.fees.values()),value)


if __name__ == '__main__':
    unittest.main()
