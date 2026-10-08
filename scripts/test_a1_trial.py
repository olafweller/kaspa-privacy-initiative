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


class FakeClock:
    def __init__(self): self.now = 0
    def monotonic(self): return self.now
    def sleep(self,seconds): self.now += seconds


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

    def test_retained_prefix_is_below_tip_with_checked_selected_parent_headers(self):
        code='''import assert from 'node:assert/strict';import {retainedBlock} from './scripts/a1_trial_rpc.mjs';
const hash=i=>i.toString(16).padStart(64,'0');let requests=0;
const rpc={async getBlock(p){requests++;assert.equal(p.includeTransactions,false);const i=parseInt(p.hash,16);
return {block:{header:{hash:p.hash,blueScore:1000n-BigInt(i)},verboseData:{selectedParentHash:hash(i+1),isChainBlock:i>=64}}};}};
const block=await retainedBlock(rpc,hash(0));assert.equal(block.header.hash,hash(64));assert.equal(requests,65);
for(const mutation of [b=>b.header.hash=hash(99),b=>b.header.blueScore=1000n,b=>b.verboseData.selectedParentHash=b.header.hash,b=>b.verboseData.isChainBlock=false]) {
const broken={async getBlock(p){const {block}=await rpc.getBlock(p);mutation(block);return {block};}};
await assert.rejects(retainedBlock(broken,hash(0)));}
console.log('{}');'''
        t.subprocess.run(['node','--input-type=module','-e',code],cwd=t.ROOT,check=True,capture_output=True,text=True)

    def test_reorg_still_halts_and_retains_the_exact_offending_response(self):
        with tempfile.TemporaryDirectory() as directory:
            trial=self.make_trial(directory);trial.locator=lambda:(self.locator,self.checkpoint)
            removed={'removedChainBlockHashes':['02'*32],'addedChainBlockHashes':[],'chainBlockAcceptedTransactions':[]}
            trial.rpc=lambda op,**kw: {'horizon':'03'*32,'utxos':[]} if op=='snapshot' else removed
            with self.assertRaisesRegex(c.Invalid,'reorg during history fetch; exact RPC evidence:'):trial.history()
            paths=list(Path(directory).glob('reorg-history-*.private.json'));self.assertEqual(len(paths),1)
            self.assertEqual(c.load_json(paths[0])['response'],removed);self.assertEqual(paths[0].stat().st_mode&0o777,0o600)

    def test_wasm_none_survives_json_but_missing_full_fields_still_fail(self):
        tx = body(self.manifest,(self.locator['s0_txid_hex'],7),'s0_terminal',self.d0,'44'*32)
        for item in tx['inputs']: item['sequence']=str(item['sequence'])
        code = '''import fs from 'node:fs';
import {stringify} from './scripts/a1_trial_rpc.mjs';
const tx=JSON.parse(fs.readFileSync(0,'utf8'));
tx.outputs[0].covenant=undefined;tx.outputs[0].value=BigInt(tx.outputs[0].value);
const none=JSON.parse(stringify(tx));delete tx.outputs[0].covenant;
console.log(stringify({none,missing:tx}));'''
        result=t.subprocess.run(['node','--input-type=module','-e',code],cwd=t.ROOT,
                                input=json.dumps(tx),capture_output=True,text=True,check=True)
        values=json.loads(result.stdout)
        self.assertIsNone(values['none']['outputs'][0]['covenant'])
        self.assertEqual(r.full_hash(values['none']),r.full_hash(tx))
        with self.assertRaisesRegex(c.Invalid,'incomplete Full output'): r.full_hash(values['missing'])
        values['none']['outputs'][0]['covenant']={'authorizingInput':0,'covenantId':'ab'*32}
        self.assertNotEqual(r.full_hash(values['none']),r.full_hash(tx))

    def test_only_unrelated_native_id_results_are_cached_by_exact_full_body(self):
        unrelated={'version':1,'inputs':[], 'outputs':[{'value':1,'scriptPublicKey':'0000','covenant':None}],
                   'lockTime':0,'subnetworkId':'00'*20,'gas':0,'payload':'','storageMass':0}
        unrelated['verboseData']={'transactionId':'66'*32,'hash':r.full_hash(unrelated)}
        history=copy.deepcopy(self.history)
        history['pages'][0]['response']['chainBlockAcceptedTransactions'][0]['acceptedTransactions'].append(unrelated)
        with tempfile.TemporaryDirectory() as directory:
            trial=self.make_trial(directory);trial.locator=lambda:(self.locator,self.checkpoint)
            with patch.object(r,'native_callback',return_value=fake_native) as factory:
                native=unittest.mock.Mock(side_effect=fake_native);factory.return_value=native
                trial.scan(history);trial.scan(history)
                self.assertEqual(native.call_count,1)
                poisoned=copy.deepcopy(history)
                poisoned['pages'][0]['response']['chainBlockAcceptedTransactions'][0]['acceptedTransactions'][-1]['verboseData']['transactionId']='77'*32
                with self.assertRaisesRegex(c.Invalid,'native body/hash verification failed'):trial.scan(poisoned)
                self.assertEqual(native.call_count,1)
                changed=copy.deepcopy(history)
                tx=changed['pages'][0]['response']['chainBlockAcceptedTransactions'][0]['acceptedTransactions'][-1]
                tx['outputs'][0]['value']=2;tx['verboseData']['hash']=r.full_hash(tx)
                trial.scan(changed);self.assertEqual(native.call_count,2)
                terminal=body(self.manifest,(self.locator['s0_txid_hex'],7),'s0_terminal',self.d0,'44'*32)
                history['pages'][1]=page('02'*32,['03'*32],[[terminal]]);history['utxos']=[]
                trial.scan(history);trial.scan(history)
                self.assertEqual(native.call_count,4)  # Both reserve spends rerun native Full.

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
            clock = FakeClock()
            with patch.object(trial,'discover',return_value=(history,report)) as reads, patch.object(t.time,'sleep',clock.sleep), patch.object(t.time,'monotonic',clock.monotonic):
                result = trial.observe('44'*32)
            self.assertEqual(reads.call_count,61); self.assertEqual(result['observed_seconds'],120)
            self.assertTrue(result['reserve_spent']); self.assertIs(type(result['payout_sompi']),int)

    def test_wrong_or_disappearing_payout_never_gets_a_result(self):
        history = self.terminal_history(); report = self.scan(history)
        with tempfile.TemporaryDirectory() as directory:
            trial = self.make_trial(directory)
            wrong = copy.deepcopy(history); wrong['utxos'][0]['entry']['amount']='1'
            with patch.object(trial,'discover',return_value=(wrong,report)), self.assertRaises(c.Invalid): trial.observe()
            unspent = self.scan()
            clock = FakeClock()
            with patch.object(trial,'discover',side_effect=[(history,report),(self.history,unspent)]), patch.object(t.time,'sleep',clock.sleep), patch.object(t.time,'monotonic',clock.monotonic), self.assertRaises(c.Invalid): trial.observe()
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

    def test_loser_is_an_observed_single_spend_result(self):
        history = self.terminal_history(); report = self.scan(history)
        with tempfile.TemporaryDirectory() as directory:
            trial = self.make_trial(directory); clock = FakeClock()
            with patch.object(trial,'discover',return_value=(history,report)), patch.object(t.time,'sleep',clock.sleep), patch.object(t.time,'monotonic',clock.monotonic):
                result = trial.observe('45'*32,race=True)
            self.assertEqual(result['outcome'],'lost'); self.assertFalse(result['own_tx_accepted'])
            self.assertEqual(result['txid'],'44'*32); self.assertTrue(result['single_accepted_terminal'])
            self.assertIn('reserve precies één keer uitgegeven',result['message'])
            self.assertEqual(result['observed_seconds'],120)
            self.assertEqual(len(list(Path(directory).glob('result-*.json'))),1)

    def test_loser_with_own_accepted_body_stops(self):
        history = self.terminal_history(); report = self.scan(history)
        own = body(self.manifest,(self.locator['s0_txid_hex'],7),'s0_terminal',self.d0,'45'*32)
        history['pages'][1]['response']['chainBlockAcceptedTransactions'][0]['acceptedTransactions'].append(own)
        with tempfile.TemporaryDirectory() as directory:
            trial = self.make_trial(directory)
            with patch.object(trial,'discover',return_value=(history,report)), self.assertRaises(c.Invalid): trial.observe('45'*32,race=True)
            self.assertFalse(any(Path(directory).glob('result-*.json')))

    def test_observe_and_nested_discover_share_configured_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            trial = self.make_trial(directory); trial.wait_seconds = 3; clock = FakeClock()
            trial.history = lambda: self.history
            with patch.object(trial,'scan',side_effect=c.Invalid('unknown/missing current UTXO')), patch.object(t.time,'sleep',clock.sleep), patch.object(t.time,'monotonic',clock.monotonic), self.assertRaisesRegex(TimeoutError,'observe: wait limit 3'):
                trial.observe()
            self.assertEqual(clock.now,3); self.assertIsNone(trial._deadline)
            self.assertFalse(any(Path(directory).glob('result-*.json')))

    def test_fund_and_discover_wait_limits(self):
        for action in ('fund','discover'):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as directory:
                trial = self.make_trial(directory); trial.wait_seconds = 3; clock = FakeClock()
                trial.inspect = lambda: {'parameter_consistency':True}
                t.save(Path(directory)/'manifest.json',self.manifest)
                checkpoint = dict(self.checkpoint,manifest_sha256=c.sha((Path(directory)/'manifest.json').read_bytes()))
                t.save(Path(directory)/'checkpoint.json',checkpoint)
                tx=copy.deepcopy(self.history['pages'][0]['response']['chainBlockAcceptedTransactions'][0]['acceptedTransactions'][0])
                tx['id']=tx['verboseData']['transactionId']; tx['outputs'][7]['covenant']=None
                trial.cfg.update(wallet='fixture-not-read',funding_validator='fixture-not-read')
                trial.rpc = lambda op, **kw: {'native_full':True,'transaction':tx,'index':7} if op=='fund-plan' else {'survives':True}
                trial.submit_once = lambda *args: None
                trial.history = lambda: {'pages':[],'entries':{}}
                with patch.object(trial,'scan',side_effect=c.Invalid('unknown/missing current UTXO')), patch.object(t.time,'sleep',clock.sleep), patch.object(t.time,'monotonic',clock.monotonic), self.assertRaisesRegex(TimeoutError,action+': wait limit 3'):
                    getattr(trial,action)()
                self.assertEqual(clock.now,3)

    def test_deadline_applies_to_rpc_subprocess_and_invalid_limits_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            trial = self.make_trial(directory); trial.cfg['sdk_dir']='fixture'
            with patch.object(t.time,'monotonic',return_value=0), trial.waiting('discover'), patch.object(t.subprocess,'run',return_value=t.subprocess.CompletedProcess([],0,stdout='{}')) as command:
                trial.rpc('sdk-check')
                self.assertEqual(command.call_args.kwargs['timeout'],1800)
            for value in (True,0,-1,float('nan'),float('inf')):
                with self.subTest(value=value), self.assertRaises(c.Invalid): t.Trial(dict(trial.cfg,wait_timeout_seconds=value))

    def test_python_diagnostic_full_chain_and_secret_redaction(self):
        with tempfile.TemporaryDirectory() as directory:
            secret='synthetic-secret-that-must-not-appear'
            wallet=Path(directory)/'wallet.json';t.save(wallet,{'private_key':secret})
            cfg={'wallet':str(wallet)}
            try:
                try: raise ValueError('root cause '+secret)
                except ValueError as cause: raise t.subprocess.CalledProcessError(2,['fixture'],output=secret,stderr='detail '+secret) from cause
            except Exception as error: filename=t.diagnostic(directory,error,cfg)
            record=c.load_json(filename); raw=filename.read_text()
            self.assertNotIn(secret,raw)
            self.assertIn('ValueError',record['traceback']);self.assertIn('CalledProcessError',record['type'])
            self.assertIn('Traceback',record['traceback']); self.assertIn('detail [REDACTED]',record['subprocess']['stderr'])
            self.assertEqual(filename.stat().st_mode&0o777,0o600)

    def test_cli_error_names_private_diagnostic(self):
        with tempfile.TemporaryDirectory() as directory:
            config=Path(directory)/'a1-trial.local.json';t.save(config,{'network':'mainnet','run':directory})
            result=t.subprocess.run(['python3',str(t.ROOT/'scripts/a1_trial.py'),'--config',str(config),'c','checkpoint'],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            filename=next(Path(directory).glob('error-python-*.private.json'))
            self.assertIn(str(filename),result.stderr)
            self.assertEqual(c.load_json(filename)['type'],'a1_check.Invalid')

    def test_exit_reconciles_only_actual_race_submission_and_never_retries(self):
        for attempted in (True,False):
            with self.subTest(attempted=attempted), tempfile.TemporaryDirectory() as directory:
                trial=self.make_trial(directory);trial.live=True;trial.cfg['backup']=directory
                trial.inspect=lambda: None;trial.command=lambda *args: {'claim_secret_matches':True}
                trial.locator=lambda: (self.locator,self.checkpoint)
                trial.discover=lambda: (self.history,self.scan())
                trial.check_terminal=lambda *args: {'full_valid':True}
                tx=body(self.manifest,(self.locator['s0_txid_hex'],7),'s0_terminal',self.d0,'45'*32);tx['id']='45'*32
                entry=self.history['entries'][self.locator['s0_txid_hex']+':7']
                t.save(Path(directory)/'b-exit-prepared.json',{'transaction':tx,'entry':entry})
                response={'status':'rpc-error','transactionId':tx['id'],'submission_attempted':attempted,'definitive_rejection':False}
                def rpc(op,**kw): return response if op=='submit' else {'survives':True}
                with patch.object(trial,'rpc',side_effect=rpc) as calls, patch.object(trial,'observe',return_value={'outcome':'lost'}) as observed:
                    if attempted:
                        self.assertEqual(trial.exit('b',submit_prepared=True,submit_at=0)['outcome'],'lost')
                        observed.assert_called_once_with(tx['id'],race=True)
                    else:
                        with self.assertRaises(c.Invalid): trial.exit('b',submit_prepared=True,submit_at=0)
                        observed.assert_not_called()
                    with self.assertRaises(c.Invalid): trial.exit('b',submit_prepared=True,submit_at=0)
                    self.assertEqual(sum(call.args[0]=='submit' for call in calls.call_args_list),1)

    def test_js_diagnostic_type_stack_and_secret_redaction(self):
        with tempfile.TemporaryDirectory() as directory:
            wallet=Path(directory)/'wallet.json';secret='synthetic-secret-not-for-a-log'
            t.save(wallet,{'private_key':secret})
            code='import {diagnostic} from '+json.dumps((t.ROOT/'scripts/a1_trial_rpc.mjs').as_uri())+';'+r'''
import fs from 'node:fs';const p=JSON.parse(fs.readFileSync(0));
const secret=JSON.parse(fs.readFileSync(p.wallet)).private_key;
console.log(diagnostic(p,new TypeError('private value '+secret,{cause:new Error('root '+secret)})));
'''
            result=t.subprocess.run(['node','--input-type=module','-e',code],input=json.dumps({'run_dir':directory,'wallet':str(wallet)}),capture_output=True,text=True,check=True)
            filename=Path(result.stdout.strip());record=c.load_json(filename)
            self.assertEqual(record['type'],'TypeError');self.assertIn('TypeError',record['traceback'])
            self.assertNotIn(secret,filename.read_text());self.assertEqual(len(record['causes']),2)
            self.assertEqual(filename.stat().st_mode&0o777,0o600)


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
