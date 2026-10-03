#!/usr/bin/env python3
"""Capture one successful file-only evidence command's JSON without shell writes."""
import argparse
import json
from pathlib import Path
import subprocess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path)
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    if not a.command or a.output.exists(): raise ValueError('new output and command required')
    result = subprocess.run(a.command, check=True, capture_output=True, text=True)
    value = json.loads(result.stdout)
    with a.output.open('xb') as stream:
        stream.write((json.dumps(value, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'captured': True, 'output': str(a.output)}))


if __name__ == '__main__': main()
