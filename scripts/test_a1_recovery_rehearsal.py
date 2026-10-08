#!/usr/bin/env python3
"""Public inventory isolation and native-path archive conversion tests."""
import copy
import base64
import json
from pathlib import Path
import tempfile
import unittest

import a1_check as c
import a1_recovery_rehearsal as h
from test_a1_check import schema_fixture


class RehearsalIsolationTests(unittest.TestCase):
    def test_prefunding_checkpoint_rejects_late_or_wrong_initial_state(self):
        point={'transactionId':'ab'*32,'index':7};entry={'amount':100,'scriptPublicKey':'0000','covenantId':None}
        receipt={'schema':'kpi-a1-native-checkpoint/v1','native_seed_utxo_present':True,'transactions_accepted':0,'initial_outpoint':point,'initial_entry':entry,'synthetic_genesis_hash':'cd'*32}
        h.check_prefunding_checkpoint(receipt,point,entry)
        for field,value in (('transactions_accepted',1),('transactions_accepted',False),('native_seed_utxo_present',False),('initial_outpoint',{'transactionId':'ef'*32,'index':7}),('initial_entry',{'amount':99}),('synthetic_genesis_hash','ab')):
            late=copy.deepcopy(receipt);late[field]=value
            with self.assertRaises(c.Invalid):h.check_prefunding_checkpoint(late,point,entry)

    def test_retained_initial_locator_rejects_late_changed_outpoint_or_checkpoint(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);archive=root/'archive';archive.mkdir()
            early={'s0_txid_hex':'ab'*32,'s0_index':'0','scan_start_hash':'cd'*32}
            retained=root/'retained.json';h.write_json(retained,early)
            h.write_json(archive/'locator.json',early)
            self.assertEqual(h.reuse_initial_locator(archive,retained),c.sha(retained.read_bytes()))
            for field in ('s0_txid_hex','scan_start_hash'):
                late=copy.deepcopy(early);late[field]='ef'*32;h.write_json(archive/'locator.json',late)
                with self.assertRaises(c.Invalid):h.reuse_initial_locator(archive,retained)
                self.assertEqual(c.load_json(retained),early)

    def test_benchmark_reader_does_not_weaken_artifact_reader(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'receipt.json';path.write_text('{"wall_seconds":1.5}')
            self.assertEqual(h.read_receipt(path)['wall_seconds'],1.5)
            with self.assertRaises(c.Invalid):c.load_json(path)
            for bad in ('{"wall_seconds":NaN}','{"wall_seconds":Infinity}','{"wall_seconds":1,"wall_seconds":2}'):
                path.write_text(bad)
                with self.assertRaises(c.Invalid):h.read_receipt(path)

    def test_public_export_refuses_actual_secret_before_any_copy(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);run=root/'run';run.mkdir();bundle=root/'private';bundle.mkdir()
            secret=b'\x13'*32;(bundle/'claim-secret.bin').write_bytes(secret)
            files=['report.json']+['public/'+name for name in ('inventory.json','manifest.json','owner-intent.json','setup-receipt.json')]
            for case in ('orderly-s0','orderly-s1','abrupt-s1'):
                files.extend(case+'-archive/'+name for name in ('locator.json','pages.json','entries.json','current-utxos.json','current-entries.json','source.json','native-acceptance.json'))
                files.extend(case+'-work/'+name for name in ('request.json','fresh-terminal.json','recovery-report.json'))
                files.append(case+'-terminal-chain/native-result.json')
            for relative in files:
                path=run/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'{}')
            for encoding in (secret,secret.hex().encode(),base64.b64encode(secret)):
                (run/'report.json').write_bytes(encoding)
                with self.assertRaises(c.Invalid):h.export_public_evidence(run,bundle,root/'publication')
                self.assertFalse((root/'publication').exists())
            (run/'report.json').write_bytes(b'{}')
            scan=h.export_public_evidence(run,bundle,root/'publication')
            self.assertFalse(scan['private_claim_secret_found'])
            self.assertEqual(len(scan['files']),len(files))
            self.assertFalse((root/'publication'/'claim-secret.bin').exists())

    def test_public_allowlist_excludes_original_private_and_proof_files(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);bundle=root/'original';bundle.mkdir();retained=root/'retained';retained.mkdir()
            manifest,intent,receipt=schema_fixture(bundle)
            (bundle/'claim-secret.bin').write_bytes(bytes(32))
            (bundle/'recipient-key.bin').write_bytes(bytes(32))
            (bundle/'s1_terminal.proof').write_bytes(bytes(128))
            (bundle/'s1_terminal.transaction.json').write_text('{}')
            (bundle/'stateful.json').write_text('{}')
            (bundle/'s1-pointer.json').write_text('{}')
            h.write_json(retained/'owner-intent.json',intent);h.write_json(retained/'setup-receipt.json',receipt)
            public=root/'public';_,digest=h.immutable_public_copy(bundle,retained,public)
            h.verify_inventory(public,digest)
            faults=h.inventory_faults(public,digest,root/'damaged')
            expected={branch+suffix for branch in c.BRANCHES for suffix in ('.pk','.vk','.r1cs')}
            expected.update(('s0.redeem','s1.redeem','manifest.json','owner-intent.json','setup-receipt.json'))
            paths={record['path'] for record in faults}
            self.assertTrue(expected.issubset(paths))
            self.assertTrue(all(record['rejected'] for record in faults))
            self.assertEqual(len(faults),2*len(c.load_json(public/'inventory.json')['files']))
            h.verify_inventory(public,digest)  # The retained public snapshot did not change.
            for forbidden in ('claim-secret.bin','recipient-key.bin','s1_terminal.proof','s1_terminal.transaction.json','stateful.json','s1-pointer.json'):
                self.assertFalse((public/forbidden).exists(),forbidden)
            (public/'unexpected-pointer.json').write_text('{}')
            with self.assertRaises(c.Invalid):h.verify_inventory(public,digest)
            (public/'unexpected-pointer.json').unlink()
            (public/'s1_terminal.pk').write_bytes(bytes(1))
            with self.assertRaises(c.Invalid):h.verify_inventory(public,digest)

    def test_native_archive_keeps_exact_derived_funding_and_historical_context(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);manifest,_,_=schema_fixture(root)
            entry={'amount':int(manifest['states']['s0']['R']),'scriptPublicKey':manifest['states']['s0']['spk_hex'],'blockDaaScore':1,'isCoinbase':False,'covenantId':None}
            # This is a converter unit fixture, not an accepted native transaction.
            tx={'version':1,'id':'42'*32,'inputs':[{'previousOutpoint':{'transactionId':'41'*32,'index':0},'signatureScript':'','sequence':2**64-1,'computeBudget':1}],'outputs':[{'value':entry['amount'],'scriptPublicKey':entry['scriptPublicKey'],'covenant':None}],'lockTime':0,'subnetworkId':'00'*20,'gas':0,'payload':'','mass':0}
            native={'backend':'converter-unit-fixture','network':'synthetic','synthetic_genesis_hash':'40'*32,'accepted_path':[{'transaction':tx,'input_entry':entry,'accepting_block':'43'*32,'block':'44'*32,'acceptance_data':[]}],'current_virtual_utxos':[[{'transactionId':'42'*32,'index':0},entry]]}
            archive=root/'archive';locator,horizon=h.archive_from_native(native,manifest,'ab'*32,archive)
            self.assertEqual(locator['s0_txid_hex'],'42'*32);self.assertEqual(locator['s0_index'],'0')
            self.assertEqual(horizon,'43'*32)
            pages=c.load_json(archive/'pages.json')
            self.assertEqual(pages[0]['startHash'],'40'*32)
            self.assertEqual(pages[0]['response']['chainBlockAcceptedTransactions'][0]['acceptedTransactions'][0]['verboseData']['transactionId'],'42'*32)
            self.assertEqual(c.load_json(archive/'entries.json')['41'*32+':0'],entry)
            self.assertFalse(c.load_json(archive/'source.json')['rpc_compatibility_demonstrated'])


if __name__=='__main__':unittest.main()
