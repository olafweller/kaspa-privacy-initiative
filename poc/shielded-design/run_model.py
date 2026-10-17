#!/usr/bin/env python3
"""Print the public test vector ledger. No RPC, proving, real funds or keys."""
import json
from model import Pool, ProofOracle, Wallet

oracle=ProofOracle();pool=Pool(oracle);alice,bob=Wallet('Alice'),Wallet('Bob')
initial=alice.note(1_000_000_000,'deposit')
event=pool.funded_deposit('native-deposit-1',initial,alice)
stages=[{'stage':'funded_uncredited',**pool.invariant()}]
pool.process(oracle.credit(event,initial,alice.address));stages.append({'stage':'credited',**pool.invariant()})
change,received=alice.note(600_000_000,'change'),bob.note(400_000_000,'receipt')
transfer=oracle.spend(alice,[initial],[(change,alice.address),(received,bob.address)],list(pool.commitments))
pool.process(transfer);stages.append({'stage':'private_transfer',**pool.invariant()})
found=bob.discover(pool.outputs);assert found==[received]
withdrawal=oracle.spend(bob,found,[],list(pool.commitments),withdrawal={'recipient':'bob-native-p2pk','amount':400_000_000})
pool.fund_rent(50_000_000)
out=pool.process(withdrawal);stages.append({'stage':'unpaid_exit',**pool.invariant()})
paid=pool.payout(out['id'],'bob-native-p2pk',400_000_000,50_000_000,600_000_000)
stages.append({'stage':'native_payout_modelled',**pool.invariant()})
print(json.dumps({'scope':'LOCAL_IDEAL_PROOF_ORACLE_ECONOMIC_MODEL_NOT_ZK_OR_TN10',
 'stagesSompi':stages,'bobIndependentDiscoveryInModel':True,'modelledPaidSompi':paid,
 'externalPermissionRentFundedSompi':pool.rent_external_funded,'permissionRentPaidSompi':pool.rent_paid,
 'realFinancialPrivacyEstablished':False,'actualNativePayout':False},indent=2))
