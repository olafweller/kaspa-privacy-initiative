#!/usr/bin/env python3
"""Repair rounded derived header nonces, preserving every original RPC/proof member.

One-shot migration from the PR31 archive; no live replay. Original published
archive remains retrievable at commit 6810058. Idempotent after migration.
"""
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1] / 'evidence/cloud-tn10'


def repair():
    path = ROOT / 'successful-trial-public.tar.gz'
    old_bytes = path.read_bytes()
    headers = {}
    origins = {}

    def collect(value, origin):
        if isinstance(value, dict):
            if 'nonce' in value and 'hash' in value:
                key = value['hash']
                assert key not in headers or headers[key]['nonce'] == value['nonce'], 'conflicting RPC header'
                headers[key] = value
                origins.setdefault(key, origin)
            for item in value.values():
                collect(item, origin)
        elif isinstance(value, list):
            for item in value:
                collect(item, origin)

    with tarfile.open(fileobj=io.BytesIO(old_bytes)) as archive:
        members = [(copy.copy(m), archive.extractfile(m).read() if m.isfile() else None)
                   for m in archive]
    for member, data in members:
        if member.name.endswith('.json') and 'rpc' in member.name:
            records = json.loads(data)
            for index, record in enumerate(records):
                collect(json.loads(record['raw']), {'rpc_member': member.name, 'record_index': index})

    changes = []

    def fix(value, member, pointer=''):
        if isinstance(value, dict):
            key = value.get('hash')
            if 'nonce' in value and key in headers and value['nonce'] != headers[key]['nonce']:
                changes.append({'member': member, 'pointer': pointer + '/nonce',
                                'rounded': value['nonce'], 'exact': headers[key]['nonce'],
                                'source': origins[key]})
                value['nonce'] = headers[key]['nonce']
            for key, item in value.items():
                fix(item, member, pointer + '/' + key)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                fix(item, member, pointer + '/' + str(index))

    rewritten = []
    for member, data in members:
        count = len(changes)
        if data is not None and member.name.endswith('.json') and 'rpc' not in member.name:
            value = json.loads(data)
            fix(value, member.name)
            if len(changes) > count:
                data = (json.dumps(value, indent=2) + '\n').encode()
                member.size = len(data)
        rewritten.append((member, data))
    if not changes:
        print('Archive already exact; no changes')
        return
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w') as archive:
        for member, data in rewritten:
            archive.addfile(member, io.BytesIO(data) if data is not None else None)
    corrected = gzip.compress(output.getvalue(), mtime=0)
    # Every raw record and binary member must survive byte-for-byte.
    with tarfile.open(fileobj=io.BytesIO(corrected)) as archive:
        for member, data in members:
            if data is not None and ('rpc' in member.name or not member.name.endswith('.json')):
                assert archive.extractfile(member.name).read() == data
    path.write_bytes(corrected)
    note_path = ROOT / 'integer-correction.json'
    note = json.loads(note_path.read_text())
    note['archive_correction'] = {'previous_sha256': hashlib.sha256(old_bytes).hexdigest(),
                                  'corrected_sha256': hashlib.sha256(corrected).hexdigest(),
                                  'changes': changes,
                                  'raw_rpc_and_binary_members_byte_identical': True}
    note['correction'] = ('Derived acceptances and public archive header nonces are re-extracted '
                          'with exact integers from byte-preserved RPC strings. Original published '
                          'derivatives/archive remain at commit 6810058. No old proof/transaction rerun.')
    note_path.write_text(json.dumps(note, indent=2) + '\n')
    manifest_path = ROOT / 'sha256.json'
    manifest = json.loads(manifest_path.read_text())
    for file in [path, note_path]:
        manifest[file.name] = hashlib.sha256(file.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print('Repaired', len(changes), 'archive nonce derivatives; original RPC/proof bytes retained')


if __name__ == '__main__':
    repair()
