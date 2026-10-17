#!/usr/bin/env python3
"""Regression: rederive historical observation JSON from byte-preserved RPC strings.

No network, node, wallet, proof generation or rewriting of original archives.
"""
import gzip
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1] / 'evidence/cloud-tn10'


def exact_observations():
    records = json.loads(gzip.decompress((ROOT / 'settlement-rpc-records.json.gz').read_bytes()))
    txid = 'ad65b24e74d8e4f2d225089265bac635357d88b51a84a34e20f7a6f66c551d67'
    for index, record in enumerate(records):
        reply = json.loads(record['raw'])
        for block in reply.get('params', {}).get('chainBlockAcceptedTransactions', []):
            for tx in block['acceptedTransactions']:
                if tx['verboseData']['transactionId'] == txid:
                    settlement = {'acceptingHeader': block['chainBlockHeader'], 'transaction': tx}
                    source = {'file': 'settlement-rpc-records.json.gz', 'record_index': index}
                    break
    assert settlement['acceptingHeader']['nonce'] == 3037550573469842379
    old = json.loads((ROOT / 'bootstrap-accepted.json').read_text())
    member = 'trial-2026-10-16T23-25-52-928Z-9510ed7d/bootstrap-rpc-records.json'
    with tarfile.open(ROOT / 'successful-trial-public.tar.gz') as archive:
        records = json.load(archive.extractfile(member))
    for index, record in enumerate(records):
        for block in json.loads(record['raw']).get('params', {}).get('chainBlockAcceptedTransactions', []):
            if block['chainBlockHeader']['hash'] == old['hash']:
                bootstrap = block['chainBlockHeader']
                bootstrap_source = {'file': 'successful-trial-public.tar.gz', 'member': member,
                                    'record_index': index}
                break
    assert bootstrap['nonce'] == 3037550572497114884
    return [('settlement-accepted.json', settlement, source),
            ('bootstrap-accepted.json', bootstrap, bootstrap_source)]


if __name__ == '__main__':
    for name, exact, _source in exact_observations():
        assert json.loads((ROOT / name).read_text()) == exact, name
    note = json.loads((ROOT / 'integer-correction.json').read_text())
    with tarfile.open(ROOT / 'successful-trial-public.tar.gz') as archive:
        for change in note.get('archive_correction', {}).get('changes', []):
            value = json.load(archive.extractfile(change['member']))
            for component in change['pointer'].strip('/').split('/'):
                value = value[int(component)] if isinstance(value, list) else value[component]
            assert value == change['exact'], change['member']
    print('PASS: both derived acceptances equal original RPC records, including exact u64 nonce')
