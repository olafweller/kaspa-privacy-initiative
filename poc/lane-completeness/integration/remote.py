#!/usr/bin/env python3
"""Use the existing authenticated VPS terminal; never print its secret.

Run from the repository root after the documented client bootstrap. File transfer
is base64 inside an ordinary shell command, without a new listener or RPC proxy.
The remote root directory is fixed to this experiment. No automatic mutation retry.
"""
import argparse
import base64
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import sys

ROOT = '/opt/kpi-pr31-cloud-20261017'
CLIENT = '.local/codex-cloud-tn10/admin/vps-exec.mjs'


def run(command):
    env = os.environ.copy()
    env['VPS_ADMIN_TOKEN'] = env['TN10_RPC_TOKEN']
    result = subprocess.run(['node', CLIENT, '--timeout-ms', '0', '--command', command],
                            env=env, text=True, capture_output=True)
    if result.returncode and not result.stdout:
        raise RuntimeError('Terminal transport failed; remote outcome unknown. Inspect before retrying.')
    response = json.loads(result.stdout)
    return response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='op', required=True)
    p = sub.add_parser('exec'); p.add_argument('command')
    p = sub.add_parser('put'); p.add_argument('source'); p.add_argument('name')
    p = sub.add_parser('get'); p.add_argument('name'); p.add_argument('destination')
    args = parser.parse_args()
    if args.op == 'exec':
        response = run(args.command)
        sys.stdout.write(response['output'])
    else:
        # Only paths inside this experiment, never wallet/private files.
        name = PurePosixPath(args.name)
        if name.is_absolute() or '..' in name.parts or args.name.endswith('.key') or 'private' in args.name:
            raise ValueError('Public paths inside the experiment only')
        remote = shlex.quote(ROOT + '/' + args.name)
        if args.op == 'put':
            payload = base64.b64encode(Path(args.source).read_bytes()).decode()
            command = f"umask 077; test ! -e {remote} && printf %s {shlex.quote(payload)} | base64 -d > {remote}"
        else:
            command = f"base64 -w0 {remote}"
        response = run(command)
        if args.op == 'get' and response['exitCode'] == 0:
            with Path(args.destination).open('xb') as output:
                output.write(base64.b64decode(response['output'].strip(), validate=True))
        elif args.op == 'put':
            sys.stdout.write(response['output'])
    raise SystemExit(0 if response['exitCode'] == 0 else 1)


if __name__ == '__main__':
    main()
