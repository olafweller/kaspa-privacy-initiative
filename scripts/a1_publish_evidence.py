#!/usr/bin/env python3
"""Allowlisted public fixture export; never publishes backups or large parameters.

Run against an observed, independently checked *unfunded* bundle. Git contains
review fixtures and descriptors, not a complete recovery replica: public PK and
normalized R1CS files must be retained separately. Known recipient fixture key 1
is deliberately public and is never suitable for funding.
"""
import argparse
import hashlib
import json
from pathlib import Path

BRANCHES = ('s0_continue', 's0_terminal', 's1_terminal')


def export(bundle, retained, output):
    bundle = Path(bundle).resolve(); retained = Path(retained).resolve(); output = Path(output)
    if output.exists():
        raise ValueError('new evidence directory required')
    secret = (bundle / 'claim-secret.bin').read_bytes()
    if len(secret) != 32:
        raise ValueError('private backup shape')
    manifest = json.loads((bundle / 'manifest.json').read_text())
    receipt = json.loads((retained / 'setup-receipt.json').read_text())
    if receipt['scope'] != 'local-unfunded-fixture' or receipt['setup_randomness_retained']:
        raise ValueError('unqualified observation scope')
    if json.loads((bundle / 'independent-checker-report.json').read_text())['parameter_consistency'] is not True:
        raise ValueError('parameter inspection required')
    names = ['manifest.json', 'owner-intent.json', 'human-manifest.txt',
             'disassembly.json', 'independent-checker-report.json', 's0.redeem', 's1.redeem',
             'cases.json', 'report.json', 'synthetic-funding.transaction.json',
             'synthetic-funding.validate.json']
    names += [branch + suffix for branch in BRANCHES for suffix in
              ('.context.hex', '.layout.json', '.vk', '.proof', '.transaction.json', '.validate.json', '.measurement.json')]
    sources = [(name, bundle / name) for name in names]
    sources += [('observation/' + name, retained / name) for name in
                ('before-setup.json', 'observation.json', 'setup-receipt.json', 'final-artifact-manifest.json')]
    # Check actual private bytes and textual encodings before any publication.
    # This supplements, rather than replaces, the explicit source allowlist.
    needles = (secret, secret.hex().encode(), secret.hex().upper().encode())
    payloads = []
    for name, source in sources:
        if not source.is_file() or source.is_symlink():
            raise ValueError('regular allowlisted source required: ' + name)
        data = source.read_bytes()
        if any(needle in data for needle in needles):
            raise ValueError('actual private claim material found in public export')
        payloads.append((name, data))
    output.mkdir(parents=True)
    entries = {}
    for name, data in payloads:
        target = output / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        entries[name] = {'bytes': str(len(data)), 'sha256': hashlib.sha256(data).hexdigest()}
    large = {branch: {kind: manifest['branches'][branch][kind] for kind in ('pk', 'r1cs')}
             for branch in BRANCHES}
    index = {'schema': 'kpi-a1-public-evidence/v1', 'scope': 'unfunded-known-recipient-key-1',
             'manifest_sha256': hashlib.sha256((bundle / 'manifest.json').read_bytes()).hexdigest(),
             'source_commit': manifest['pins']['kpi_source_commit'], 'files': entries,
             'external_public_artifacts_required': large,
             'complete_recovery_bundle_in_git': False, 'private_claim_value_scan_passed': True,
             'recipient_fixture_private_key_is_public': True, 'funding_authorized': False}
    (output / 'public-evidence-index.json').write_text(json.dumps(index, indent=2, sort_keys=True) + '\n')
    return {'exported_files': len(entries), 'public_bytes': sum(int(x['bytes']) for x in entries.values()),
            'manifest_sha256': index['manifest_sha256'], 'complete_recovery_bundle_in_git': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--verify-only', action='store_true', help='scan actual claim value without writing')
    p.add_argument('bundle', type=Path); p.add_argument('retained', type=Path); p.add_argument('output', type=Path, nargs='?')
    a = p.parse_args()
    if a.verify_only:
        secret = (a.bundle / 'claim-secret.bin').read_bytes()
        if len(secret) != 32: raise ValueError('private backup shape')
        needles = (secret, secret.hex().encode(), secret.hex().upper().encode())
        count = 0
        for path in a.retained.rglob('*'):
            if path.is_file():
                if path.is_symlink() or any(value in path.read_bytes() for value in needles):
                    raise ValueError('private value/symlink in proposed evidence')
                count += 1
        print(json.dumps({'actual_private_claim_value_absent': True, 'files_scanned': count}))
    else:
        if a.output is None: raise ValueError('new output required')
        print(json.dumps(export(a.bundle, a.retained, a.output), indent=2))


if __name__ == '__main__':
    main()
