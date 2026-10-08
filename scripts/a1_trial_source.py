#!/usr/bin/env python3
"""Rebuild or verify the exact sources deployed in the 2026-10-08 A1 trial.

The published templates under poc/a1/evidence/official-trial-2026-10-08/source
replace machine-local values (paths, the C host address and SSH aliases) with
placeholders. Given the operator's private values file, `verify` proves that
substituting them reproduces every deployed file byte for byte, and
`materialize` writes the reproduced files to a new directory.
"""
import argparse
import hashlib
import json
import pathlib
import sys

DEFAULT_SOURCE = (pathlib.Path(__file__).resolve().parents[1]
                  / 'poc/a1/evidence/official-trial-2026-10-08/source')


def load(source):
    manifest = json.loads((source / 'MANIFEST.json').read_bytes())
    listed = set(manifest['files'])
    present = {str(p.relative_to(source)) for p in source.rglob('*')
               if p.is_file() and p.name != 'MANIFEST.json'}
    if listed != present:
        raise SystemExit(f'manifest mismatch: missing={sorted(listed - present)} '
                         f'unlisted={sorted(present - listed)}')
    return manifest


def render(text, values):
    for token, value in values.items():
        text = text.replace(token, value)
    return text


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['verify', 'materialize'])
    parser.add_argument('--values', type=pathlib.Path, required=True,
                        help='private JSON object mapping each placeholder to its value')
    parser.add_argument('--source', type=pathlib.Path, default=DEFAULT_SOURCE)
    parser.add_argument('--output', type=pathlib.Path,
                        help='new directory for materialize')
    args = parser.parse_args(argv)
    manifest = load(args.source)
    values = json.loads(args.values.read_bytes())
    if sorted(values) != sorted(manifest['placeholders']):
        raise SystemExit('values must define exactly: ' + ', '.join(manifest['placeholders']))
    if args.action == 'materialize':
        if args.output is None:
            raise SystemExit('materialize needs --output')
        args.output.mkdir(parents=True, exist_ok=False)
    bad = []
    for rel, entry in sorted(manifest['files'].items()):
        raw = render((args.source / rel).read_text('utf-8'), values).encode('utf-8')
        if hashlib.sha256(raw).hexdigest() != entry['deployed_sha256']:
            bad.append(rel)
        if args.action == 'materialize':
            dest = args.output / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
    print(json.dumps({'run_id': manifest['run_id'], 'files': len(manifest['files']),
                      'matching': len(manifest['files']) - len(bad), 'mismatched': bad}))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
