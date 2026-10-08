#!/usr/bin/env python3
"""Offline runner adversaries. Synthetic chain assertions are never TN10 evidence."""
import copy
import hashlib
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
    def setUp(self):
        self.manifest, self.locator, self.d0, self.d1 = fixtures()
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

    def test_wrong_network_rejected(self):
        with self.assertRaises(c.Invalid): t.Trial({'network':'mainnet'})


@unittest.skipUnless(os.environ.get('KPI_A1_TRIAL_INTEGRATION_CONFIG'), 'explicit local integration config required')
class NativeIntegrationTests(unittest.TestCase):
    def test_fresh_s0_both_roles_sdk_full_and_tampered_archive(self):
        config = c.load_json(os.environ['KPI_A1_TRIAL_INTEGRATION_CONFIG'])
        trial = t.Trial(config)
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
        mutated = copy.deepcopy(transaction); mutated['inputs'][0]['signatureScript']='00'
        with self.assertRaises((c.Invalid,t.subprocess.SubprocessError)): trial.check_terminal(mutated,entry,'b')
        mutated = copy.deepcopy(transaction); mutated['outputs'][0]['value']=str(int(mutated['outputs'][0]['value'])+1)
        with self.assertRaises(c.Invalid): trial.check_terminal(mutated,entry,'b')
        broken = copy.deepcopy(history); broken['pages'][1]['response']['chainBlockAcceptedTransactions'][0]['acceptedTransactions'][0]['verboseData']['hash']='00'*32
        with self.assertRaises(c.Invalid): trial.scan(broken)
        self.assertFalse(any(trial.run.glob('*submission*.json')))
        t.save(trial.run/'offline-integration-result.json',{'scope':'synthetic history, real fresh proofs/native Full/pinned SDK; no node acceptance',
             'a_b_distinct_txids':ids,'network_used':False,'test_kas_used':False,'native_full_sdk_passed':True})


if __name__ == '__main__': unittest.main()
