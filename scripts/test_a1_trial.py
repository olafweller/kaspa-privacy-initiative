#!/usr/bin/env python3
"""Offline runner adversaries. Synthetic chain assertions are never TN10 evidence."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import a1_check as c
import a1_recovery as r
import a1_trial as t
from test_a1_recovery import fixtures, body, page, fake_native


def synthetic_history(manifest, locator):
    funding = {'version':0, 'inputs':[], 'outputs':[{'value':0,'scriptPublicKey':'0000'} for _ in range(8)],
               'lockTime':0, 'subnetworkId':'00'*20, 'gas':0, 'payload':'', 'storageMass':0}
    funding['outputs'][7] = {'value':int(manifest['states']['s0']['R']), 'scriptPublicKey':manifest['states']['s0']['spk_hex']}
    txid = hashlib.blake2b(r.canonical_body(funding, False), digest_size=32, key=b'TransactionID').hexdigest()
    funding['verboseData'] = {'transactionId':txid, 'hash':r.full_hash(funding)}
    locator['s0_txid_hex'] = txid
    entry = {'amount':int(manifest['states']['s0']['R']), 'scriptPublicKey':manifest['states']['s0']['spk_hex'],
             'blockDaaScore':2, 'isCoinbase':False, 'covenantId':None}
    return {'horizon':'03'*32, 'pages':[page('01'*32,['02'*32],[[funding]]), page('02'*32,['03'*32],[[]])],
            'utxos':[{'outpoint':{'transactionId':txid,'index':7},'entry':entry}], 'entries':{txid+':7':entry}}


class TrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_root = t.ROOT/'.local/a1-trial-tests'
        cls.temp_root.mkdir(parents=True, mode=0o700, exist_ok=True)
        cls.old_tempdir = tempfile.tempdir; tempfile.tempdir = str(cls.temp_root)

    @classmethod
    def tearDownClass(cls): tempfile.tempdir = cls.old_tempdir

    def setUp(self):
        self.manifest, self.locator, self.d0, self.d1 = fixtures()
        self.manifest['recipient']['address'] = 'kaspatest:synthetic-fixture-only'
        self.history = synthetic_history(self.manifest, self.locator)
        self.checkpoint = {'hash':'01'*32,'blue_score':'1','daa_score':'2','manifest_sha256':'ab'*32,
                           'instance_hex':self.manifest['instance_hex'],'genesis_hex':self.manifest['genesis_hex']}

    def scan(self, history=None, checkpoint=None):
        return t.scan_history(self.manifest, self.locator, checkpoint or self.checkpoint, history or self.history, fake_native)

    def test_s0_funding_is_authenticated_not_an_address_guess(self):
        report = self.scan()
        self.assertTrue(report['lineage_history_complete']); self.assertEqual(report['state'],'s0')
        self.assertEqual(report['paid'],'0')

    def test_missing_corrupt_reordered_history_stops_before_submission(self):
        cases = []
        x = copy.deepcopy(self.history); x['pages'].pop(0); cases.append(x)
        x = copy.deepcopy(self.history); x['pages'].pop(); cases.append(x)
        x = copy.deepcopy(self.history); x['pages'].reverse(); cases.append(x)
        x = copy.deepcopy(self.history); x['pages'][0]['response']['chainBlockAcceptedTransactions']=[]; cases.append(x)
        x = copy.deepcopy(self.history); x['pages'][0]['response']['chainBlockAcceptedTransactions'][0]['acceptedTransactions'][0]['outputs'][7]['value']+=1; cases.append(x)
        x = copy.deepcopy(self.history); x['pages'][0]['startHash']='ff'*32; cases.append(x)
        x = copy.deepcopy(self.history); x['horizon']='ff'*32; cases.append(x)
        for history in cases:
            with self.subTest(history=history), patch.object(t.Trial,'submit_once') as submit:
                with self.assertRaises(c.Invalid): self.scan(history)
                submit.assert_not_called()

    def test_wrong_checkpoint_cross_instance_and_reorg_stop(self):
        for field in ('hash','blue_score','daa_score','manifest_sha256','instance_hex','genesis_hex'):
            wrong = dict(self.checkpoint); wrong[field]='ff'*32
            with self.subTest(field=field), self.assertRaises(c.Invalid): self.scan(checkpoint=wrong)
        x = copy.deepcopy(self.history); x['pages'][1]['response']['removedChainBlockHashes']=['02'*32]
        with self.assertRaises(c.Invalid): self.scan(x)

    def test_utxo_amount_type_boundary_and_duplicate(self):
        x = copy.deepcopy(self.history); x['utxos'][0]['entry']['amount']=str(x['utxos'][0]['entry']['amount'])
        self.assertTrue(self.scan(x)['current_utxo_reconciled'])
        for value in (-1, True, 1.0, str(2**64), str(c.MAX_SOMPI+1)):
            with self.subTest(value=value), self.assertRaises(c.Invalid): t.sompi(value)
        for value in (0, c.MAX_SOMPI, str(c.MAX_SOMPI)): self.assertEqual(t.sompi(value),int(value))
        x = copy.deepcopy(self.history); x['utxos']*=2
        with self.assertRaises(c.Invalid): self.scan(x)

    def test_synthetic_s0_exit_and_conflicting_spend(self):
        tx = body(self.manifest,(self.locator['s0_txid_hex'],7),'s0_terminal',self.d0,'44'*32)
        x = copy.deepcopy(self.history); x['pages'][1]=page('02'*32,['03'*32],[[tx]]); x['utxos']=[]
        result = self.scan(x)
        self.assertEqual(result['state'],'terminal'); self.assertEqual(len(result['transitions']),1)
        other = body(self.manifest,(self.locator['s0_txid_hex'],7),'s0_terminal',self.d0,'45'*32)
        x['pages'][1]['response']['chainBlockAcceptedTransactions'][0]['acceptedTransactions'].append(other)
        with self.assertRaises(c.Invalid): self.scan(x)

    def make_trial(self, directory):
        trial = t.Trial({'network':'testnet-10','run':directory,'bundle':directory,'binary':'unused','reference_binary':'unused'})
        trial.manifest = lambda: self.manifest
        return trial

    def test_network_default_denies_before_process_spawn(self):
        with tempfile.TemporaryDirectory() as directory:
            trial = self.make_trial(directory)
            for op in ('checkpoint','fund-plan','submit','snapshot','page','survives'):
                with self.subTest(op=op), patch.object(t.subprocess,'run') as command:
                    with self.assertRaises(c.Invalid): trial.rpc(op)
                    command.assert_not_called()

    def test_intent_survives_unknown_response_and_is_never_retried(self):
        tx = body(self.manifest,(self.locator['s0_txid_hex'],7),'s0_terminal',self.d0,'44'*32); tx['id']='44'*32
        with tempfile.TemporaryDirectory() as directory:
            trial = self.make_trial(directory); trial.live = True
            def uncertain(op, **kwargs):
                self.assertTrue((Path(directory)/'b-exit-submission-intent.json').exists())
                raise OSError('lost response')
            trial.rpc = uncertain
            with self.assertRaises(OSError): trial.submit_once('b-exit',tx)
            self.assertTrue((Path(directory)/'b-exit-submission-unknown.json').exists())
            with patch.object(trial,'rpc') as submit:
                with self.assertRaises(FileExistsError): trial.submit_once('b-exit',tx)
                submit.assert_not_called()

    def test_exclusive_private_evidence_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'intent.json'; t.save(path, {'txid':'ab'*32})
            self.assertEqual(path.stat().st_mode&0o777,0o600)
            with self.assertRaises(FileExistsError): t.save(path, {'txid':'cd'*32})
            self.assertEqual(c.load_json(path)['txid'],'ab'*32)

    def test_public_rpc_error_is_retained_without_claiming_rejection(self):
        tx = body(self.manifest,(self.locator['s0_txid_hex'],7),'s0_terminal',self.d0,'44'*32); tx['id']='44'*32
        with tempfile.TemporaryDirectory() as directory:
            trial = self.make_trial(directory); trial.live = True
            response = {'status':'rpc-error','transactionId':tx['id'],'error':'synthetic lost reply','definitive_rejection':False}
            with patch.object(trial,'rpc',return_value=response) as submit:
                with self.assertRaises(c.Invalid): trial.submit_once('b-exit',tx)
                with self.assertRaises(FileExistsError): trial.submit_once('b-exit',tx)
                self.assertEqual(submit.call_count,1)
            self.assertEqual(c.load_json(Path(directory)/'b-exit-submission-unknown.json'),response)

    def test_wrong_network_rejected(self):
        with self.assertRaises(c.Invalid): t.Trial({'network':'mainnet'})

    def test_read_only_snapshot_alignment_retry_keeps_corruption_strict(self):
        with tempfile.TemporaryDirectory() as directory:
            trial = self.make_trial(directory); trial.history = lambda: self.history
            with patch.object(trial,'scan',side_effect=[c.Invalid('unknown/missing current UTXO'), self.scan()]) as scan, patch.object(t.time,'sleep'):
                self.assertEqual(trial.discover()[1]['state'],'s0'); self.assertEqual(scan.call_count,2)
            for reason in ('wrong checkpoint','reorg during history fetch','poisoned full transaction hash','pagination missing acceptance groups'):
                with patch.object(trial,'scan',side_effect=c.Invalid(reason)), self.assertRaises(c.Invalid): trial.discover()

    def terminal_history(self):
        tx = body(self.manifest,(self.locator['s0_txid_hex'],7),'s0_terminal',self.d0,'44'*32)
        history = copy.deepcopy(self.history); history['pages'][1]=page('02'*32,['03'*32],[[tx]])
        want = self.manifest['branches']['s0_terminal']['outputs'][0]
        history['utxos']=[{'outpoint':{'transactionId':'44'*32,'index':0},'entry':dict(self.history['utxos'][0]['entry'],
                            amount=want['value'],scriptPublicKey=want['spk_hex'])}]
        return history

    def test_exact_payout_is_checked_again_at_120_seconds(self):
        history = self.terminal_history(); report = self.scan(history)
        with tempfile.TemporaryDirectory() as directory:
            trial = self.make_trial(directory)
            with patch.object(trial,'discover',return_value=(history,report)) as reads, patch.object(t.time,'sleep'), patch.object(t.time,'monotonic',side_effect=[0,0,119,120]):
                result = trial.observe('44'*32)
            self.assertEqual(reads.call_count,3); self.assertEqual(result['observed_seconds'],120)
            self.assertTrue(result['reserve_spent']); self.assertIs(type(result['payout_sompi']),int)

    def test_wrong_or_disappearing_payout_never_gets_a_result(self):
        history = self.terminal_history(); report = self.scan(history)
        with tempfile.TemporaryDirectory() as directory:
            trial = self.make_trial(directory)
            wrong = copy.deepcopy(history); wrong['utxos'][0]['entry']['amount']='1'
            with patch.object(trial,'discover',return_value=(wrong,report)), self.assertRaises(c.Invalid): trial.observe()
            unspent = self.scan()
            with patch.object(trial,'discover',side_effect=[(history,report),(self.history,unspent)]), patch.object(t.time,'sleep'), patch.object(t.time,'monotonic',side_effect=[0,0]), self.assertRaises(c.Invalid): trial.observe()
            self.assertFalse(any(Path(directory).glob('result-*.json')))

    def test_checkpoint_refuses_an_already_funded_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            trial = self.make_trial(directory); trial.inspect = lambda: {'parameter_consistency':True}
            with patch.object(trial,'rpc',return_value={'utxos':[self.history['utxos'][0]]}), self.assertRaises(c.Invalid): trial.checkpoint()
            self.assertFalse((Path(directory)/'checkpoint.json').exists())

    def test_moving_tip_export_is_trimmed_to_fixed_horizon(self):
        with tempfile.TemporaryDirectory() as directory:
            trial = self.make_trial(directory); trial.locator = lambda: (self.locator,self.checkpoint)
            self.manifest['recipient']['spk_hex'] = self.manifest['states']['s0']['spk_hex']
            responses = {'snapshot':{'horizon':'03'*32,'utxos':self.history['utxos']},
                         'page':page('01'*32,['02'*32,'03'*32,'04'*32],[[],[],[]])['response'],
                         'survives':{'survives':True}}
            trial.rpc = lambda op, **kw: responses[op]
            history = trial.history()
            self.assertEqual(history['horizon'],'03'*32)
            self.assertEqual(history['pages'][0]['response']['addedChainBlockHashes'],['02'*32,'03'*32])
            self.assertEqual(len(history['pages'][0]['response']['chainBlockAcceptedTransactions']),2)


@unittest.skipUnless(os.environ.get('KPI_A1_TRIAL_INTEGRATION_CONFIG'), 'explicit local integration config required')
class NativeIntegrationTests(unittest.TestCase):
    def test_signed_funding_plan_mock_chain_real_full(self):
        config = c.load_json(os.environ['KPI_A1_TRIAL_INTEGRATION_CONFIG'])
        if not config.get('funding_validator'): self.skipTest('explicit A0 native funding validator required')
        directory = Path(tempfile.mkdtemp(prefix='funding-integration-',dir=config['run']))
        manifest = c.load_json(Path(config['bundle'])/'manifest.json')
        payload = dict(config, op='fund-plan',rpc_url='ws://127.0.0.1:1',wallet=str(directory/'fixture-wallet.json'),
                       spk=manifest['states']['s0']['spk_hex'],amount=manifest['states']['s0']['R'],
                       context_file=str(directory/'context.json'),body_file=str(directory/'transaction.json'))
        t.save(Path(payload['wallet']), {'network':'testnet-10','private_key':'00'*31+'01'})
        # The known public key 1 is used ONLY in this synthetic wallet fixture.
        code = 'import {execute} from '+json.dumps((t.ROOT/'scripts/a1_trial_rpc.mjs').as_uri())+';'+r'''
import fs from 'node:fs';import assert from 'node:assert/strict';import {createRequire} from 'node:module';
const p=JSON.parse(fs.readFileSync(0));const k=createRequire(import.meta.url)(p.sdk_dir+'/kaspa.js');
const key=new k.PrivateKey('00'.repeat(31)+'01'),address=key.toKeypair().toAddress('testnet-10').toString();
let connected=0,submitted=0;
const rpc={connect:async()=>{connected++;},disconnect:async()=>{},
  getServerInfo:async()=>({networkId:'testnet-10',serverVersion:'2.1.0',isSynced:true,hasUtxoIndex:true}),
  getBlockDagInfo:async()=>({network:'testnet-10',sink:'01'.repeat(32),virtualDaaScore:1000n,pastMedianTime:0n}),
  getUtxosByAddresses:async()=>({entries:[{address,outpoint:{transactionId:'43'.repeat(32),index:0},
    amount:BigInt(p.amount)+2000000000n,scriptPublicKey:k.payToAddressScript(address),blockDaaScore:1n,isCoinbase:false}]}),
  submitTransaction:async()=>{submitted++;throw Error('fixture must never submit');}};
const plan=await execute(p,()=>rpc);assert.equal(plan.native_full,true);assert.equal(submitted,0);assert.equal(connected,1);
assert.equal(plan.transaction.outputs[plan.index].value,p.amount);
const error=await execute({...p,op:'submit',transaction:plan.transaction},()=>rpc);
assert.equal(error.status,'rpc-error');assert.equal(error.definitive_rejection,false);assert.equal(submitted,1);
rpc.getServerInfo=async()=>({networkId:'mainnet',serverVersion:'2.1.0',isSynced:true,hasUtxoIndex:true});
await assert.rejects(execute({...p,op:'snapshot'},()=>rpc));
console.log(JSON.stringify({native_full:true,txid:plan.transaction.id,fee_sompi:plan.fee,mock_node_only:true,
  network_used:false,fund_plan_submission_calls:0,synthetic_submission_calls:submitted,ambiguous_error_retained:true}));
'''
        result = t.subprocess.run(['node','--input-type=module','-e',code],input=json.dumps(payload),
                                  capture_output=True,text=True,check=True)
        t.save(directory/'result.json',json.loads(result.stdout))

    def test_fresh_s0_both_roles_sdk_full_and_tampered_archive(self):
        config = c.load_json(os.environ['KPI_A1_TRIAL_INTEGRATION_CONFIG'])
        parent = Path(config['run'])
        config = dict(config, run=tempfile.mkdtemp(prefix='integration-',dir=parent))
        trial = t.Trial(config)
        original = tempfile.tempdir; tempfile.tempdir = str(trial.run)
        self.addCleanup(setattr,tempfile,'tempdir',original)
        manifest = trial.manifest()
        locator = {'network':manifest['network'],'genesis_hex':manifest['genesis_hex'],'instance_hex':manifest['instance_hex'],
                   's0_txid_hex':'00'*32,'s0_index':'7','s0_amount':manifest['states']['s0']['R'],
                   's0_spk_hex':manifest['states']['s0']['spk_hex'],'s0_covenant':None,'scan_start_hash':'01'*32,
                   'scan_start_blue_score':'1','scan_start_daa_score':'2','artifact_index_sha256':c.sha((trial.bundle/'manifest.json').read_bytes())}
        checkpoint = {'hash':'01'*32,'blue_score':'1','daa_score':'2','manifest_sha256':locator['artifact_index_sha256'],
                      'instance_hex':manifest['instance_hex'],'genesis_hex':manifest['genesis_hex']}
        history = synthetic_history(manifest,locator)
        t.save(trial.run/'checkpoint.json',checkpoint); t.save(trial.run/'locator.json',locator)
        t.save(trial.run/'synthetic-history.json',history)
        ids = []
        for role in ('a','b'):
            result = trial.exit(role, history, prepare_only=True)
            self.assertFalse(result['submitted']); ids.append(result['txid'])
        self.assertNotEqual(*ids)
        prepared = c.load_json(trial.run/'b-exit-prepared.json'); entry = prepared['entry']; transaction = prepared['transaction']
        accepted = copy.deepcopy(transaction); accepted['verboseData']={'transactionId':transaction['id'],'hash':r.full_hash(transaction)}
        history['pages'][1]=page('02'*32,['03'*32],[[accepted]])
        history['utxos']=[{'outpoint':{'transactionId':transaction['id'],'index':0},'entry':dict(entry,
                          amount=int(transaction['outputs'][0]['value']),scriptPublicKey=transaction['outputs'][0]['scriptPublicKey'])}]
        self.assertEqual(trial.scan(history)['state'],'terminal')
        mutated = copy.deepcopy(transaction)
        witness = bytearray.fromhex(mutated['inputs'][0]['signatureScript']); witness[68]^=1
        mutated['inputs'][0]['signatureScript']=witness.hex()
        with self.assertRaises((c.Invalid,t.subprocess.SubprocessError)): trial.check_terminal(mutated,entry,'b')
        mutated = copy.deepcopy(transaction); mutated['outputs'][0]['value']=str(int(mutated['outputs'][0]['value'])+1)
        with self.assertRaises(c.Invalid): trial.check_terminal(mutated,entry,'b')
        broken = copy.deepcopy(history); broken['pages'][1]['response']['chainBlockAcceptedTransactions'][0]['acceptedTransactions'][0]['verboseData']['hash']='00'*32
        with self.assertRaises(c.Invalid): trial.scan(broken)
        self.assertFalse(any(trial.run.glob('*submission*.json')))
        t.save(trial.run/'offline-integration-result.json',{'scope':'synthetic history, real fresh proofs/native Full/pinned SDK; no node acceptance',
             'a_b_distinct_txids':ids,'network_used':False,'test_kas_used':False,'native_full_sdk_passed':True})


if __name__ == '__main__': unittest.main()
