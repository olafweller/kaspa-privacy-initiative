#!/usr/bin/env python3
"""Repeat the unchanged offline A0 harness; never load wallet configuration."""
import argparse
import hashlib
import json
import os
import platform
import statistics
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, default=5)
    args = parser.parse_args()
    if not 3 <= args.samples <= 20:
        parser.error('--samples must be between 3 and 20')
    root = Path(__file__).resolve().parent.parent
    runner = root / 'scripts/run_poc_a0.sh'
    records = []
    with tempfile.TemporaryDirectory(prefix='kpi-a0-benchmark-') as directory:
        for index in range(args.samples):
            rss = Path(directory) / 'rss.txt'
            run = subprocess.run(
                ['/usr/bin/time', '-f', '%M', '-o', str(rss), str(runner)],
                cwd=root, text=True, capture_output=True, check=True,
            )
            record = json.loads(run.stdout)
            cases = record['cases']
            assert len(cases) == 30
            assert sum(not case['accepted'] for case in cases) == 28
            assert all(case['accepted'] == case['expected_accept'] for case in cases)
            record['sample'] = index + 1
            record['maximum_resident_set_size_kib'] = int(rss.read_text().strip())
            records.append(record)
    cpu = next((line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                if line.startswith('model name')), 'unknown')
    os_release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines()
                      if '=' in line)
    summary = {}
    for key in ['setup_ms', 'proving_ms', 'standalone_verify_ms', 'maximum_resident_set_size_kib']:
        values = [record[key] for record in records]
        summary[key] = {'min': min(values), 'median': statistics.median(values), 'max': max(values)}
    values = [record['cases'][0]['validation_ms'] for record in records]
    summary['full_valid_transaction_validation_ms'] = {
        'min': min(values), 'median': statistics.median(values), 'max': max(values),
    }
    files = ['poc/a0/src/main.rs', 'poc/a0/src/circuit.rs', 'poc/a0/Cargo.lock',
             'poc/a0/Cargo.toml', 'scripts/run_poc_a0.sh']
    result = {
        'observed_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Repeated offline supplied-UTXO fixture; no live transaction or adapter tested',
        'environment': {
            'cpu': cpu, 'logical_cpus': os.cpu_count(),
            'os': os_release.get('PRETTY_NAME', 'unknown').strip('"'),
            'kernel': platform.release(),
            'rustc': subprocess.check_output(['rustc', '+1.91.0', '--version'], text=True).strip(),
            'build_profile': 'release',
            'rayon_num_threads': os.environ.get('RAYON_NUM_THREADS', 'default'),
        },
        'measurement_notes': [
            'Fresh independent setup/proof each sample; existing optimized build cache.',
            'GNU time maximum RSS covers the entire harness, not just proof generation.',
            'RSS is maximum reported process residency, not aggregate memory across simultaneous processes.',
            'Transaction bytes are the upstream estimate, not captured TN10 RPC serialization.',
            'Shared desktop measurements; no throughput or cryptographic-correctness claim.',
        ],
        'source_sha256': {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files},
        'summary': summary, 'samples': records,
    }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
