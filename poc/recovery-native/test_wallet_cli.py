#!/usr/bin/env python3
"""Offline new-root wallet bridge; never reads pre-existing wallet secrets."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
BIN = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT.parents[1] / '.local/ci-target/release/kpi-recovery-native-wallet'

def call(args, success=True):
    p = subprocess.run([str(BIN), *map(str, args)], capture_output=True, text=True, timeout=120)
    assert (p.returncode == 0) == success, (args, p.returncode, p.stderr[:500])
    return p

def main():
    targets = json.loads((ROOT / 'evidence/targets.json').read_text())['batches']
    stages = ['deposit', 'credit-transfer', 'bob-exit', 'bob-reconcile', 'alice-exit', 'alice-reconcile']
    files = [ROOT / 'evidence/fixtures' / (s + '.input.bin') for s in stages]
    start = targets['deposit']['expectedJournalHex'][:64]
    end = targets['alice-reconcile']['expectedJournalHex'][128:192]
    with tempfile.TemporaryDirectory(prefix='kpi-new-relation-wallet-') as tmp:
        t = Path(tmp)
        call(['init', t / 'own'])
        receive = json.loads((t / 'own/receive.json').read_text())
        assert set(receive) == {'schema', 'domain', 'owner', 'incoming'}
        assert (t / 'own/wallet.backup').stat().st_mode & 0o777 == 0o600
        assert (t / 'own/native.key').stat().st_mode & 0o777 == 0o600
        call(['init', t / 'own'], False)
        p = call(['rebuild', start, end, t / 'restored.bin', *files])
        assert (t / 'restored.bin').read_bytes() == (ROOT / 'evidence/fixtures/alice-reconcile.state.bin').read_bytes()
        assert json.loads(p.stdout)['accounting']['reserve_principal'] == 0
        assert json.loads(call(['scan', t / 'restored.bin', end, t / 'own']).stdout)['spendableSompi'] == 0
        p = call(['exit', t / 'restored.bin', end, t / 'own', t / 'no-parameters', t / 'no-exit'], False)
        assert 'current recovered note' in p.stderr
        p = call(['scan', t / 'restored.bin', '00' * 32, t / 'own'], False)
        assert 'expected accepted state root' in p.stderr
        for order in [files[1:], files[::-1]]:
            p = call(['rebuild', start, end, t / 'missing-state.bin', *order], False)
            assert 'history discontinuity' in p.stderr
        # A genuine OLD snapshot/old accepted root belongs to another relation.
        old = ROOT.parent / 'tn10-live/evidence/reconcile'
        old_root = json.loads((old / 'accepted-checkpoint.json').read_text())['stateRoot']
        p = call(['scan', old / 'state.bin', old_root, t / 'own'], False)
        assert 'expected accepted state root' in p.stderr
        print(json.dumps({'scope': 'NEW_RELATION_OFFLINE_WALLET_BRIDGE_NOT_INDEPENDENT_CUSTODY_OR_TN10', 'sixBatchesReconstructedExactly': True, 'sharedReceiveFields': sorted(receive), 'oldRelationRootRejected': True, 'unauthorizedExitRejected': True, 'missingAndReorderedHistoryRejected': True, 'initOverwriteRejected': True, 'wrongRootRejected': True, 'newOuterProofs': 0, 'RPC': False}, indent=2))

if __name__ == '__main__':
    main()
