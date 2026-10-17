#!/usr/bin/env python3
"""Read RISC Zero's public pprof wire format; report observed bigint2 stacks.

These are executor diagnostics, not cryptographically proven cost accounting.
No dependency inclusion or string presence alone is counted as execution.
"""
from collections import Counter
import gzip
import json
from pathlib import Path
import sys


def varint(data, offset):
    value = shift = 0
    while True:
        byte = data[offset]
        offset += 1
        value |= (byte & 127) << shift
        if not byte & 128:
            return value, offset
        shift += 7
        assert shift <= 63


def fields(data):
    offset = 0
    result = {}
    while offset < len(data):
        tag, offset = varint(data, offset)
        number, wire = tag >> 3, tag & 7
        if wire == 0:
            value, offset = varint(data, offset)
        elif wire == 2:
            length, offset = varint(data, offset)
            value = data[offset:offset + length]
            offset += length
        else:
            raise ValueError(f'unsupported pprof wire type {wire}')
        assert offset <= len(data)
        result.setdefault(number, []).append(value)
    return result


def integers(values):
    result = []
    for value in values:
        if isinstance(value, int):
            result.append(value)
        else:
            offset = 0
            while offset < len(value):
                item, offset = varint(value, offset)
                result.append(item)
    return result


raw = Path(sys.argv[1]).read_bytes()
profile = fields(gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw)
strings = [item.decode() for item in profile[6]]
sample_types = [(strings[item[1][0]], strings[item[2][0]])
                for item in map(fields, profile[1])]
assert sample_types == [('cycles', 'count')]
functions = {item[1][0]: strings[item[2][0]]
             for item in map(fields, profile.get(5, []))}
locations = {item[1][0]: [functions[line[1][0]]
                        for line in map(fields, item.get(4, []))]
             for item in map(fields, profile.get(4, []))}
cycles = Counter()
samples = Counter()
for item in map(fields, profile.get(2, [])):
    names = {name for location in integers(item.get(1, []))
             for name in locations[location] if 'bigint2' in name}
    weight, = integers(item[2])
    for name in names:
        cycles[name] += weight
        samples[name] += 1
assert any(name.startswith('sys_bigint2_') and cycles[name] > 0 for name in cycles)
result = {
    'scope': 'EXECUTOR_PPROF_OBSERVED_SAMPLED_STACKS_NOT_PROVEN_GAS',
    'acceleratedPathObserved': True,
    'functions': [{'name': name, 'samples': samples[name],
                   'inclusiveDiagnosticCycles': cycles[name]}
                  for name in sorted(cycles)],
    'note': 'Overlapping inclusive stacks; counts are not syscall invocation counts.',
}
with Path(sys.argv[2]).open('x') as output:
    output.write(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
