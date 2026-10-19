#!/usr/bin/env python3
"""Offline separate-process replay and rejection controls. No user secrets read."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BIN = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / '.local/ci-target/release/user-recovery'
LIVE = ROOT / 'poc/tn10-live/evidence'

def call(args, success=True):
    p = subprocess.run([str(BIN), *map(str, args)], text=True, capture_output=True, timeout=120)
    assert (p.returncode == 0) == success, (args, p.returncode, p.stderr[:500])
    return p


def main():
    stages = ['deposit', 'credit-transfer', 'exit', 'reconcile']
    targets = [json.loads((LIVE / s / 'target.json').read_text()) for s in stages]
    first_root = targets[0]['journalHex'][:64]
    last_root = targets[-1]['journalHex'][128:192]
    inputs = [LIVE / s / 'input.bin' for s in stages]
    with tempfile.TemporaryDirectory(prefix='kpi-user-recovery-') as tmp:
        t = Path(tmp)
        rebuilt = t / 'reconstructed.bin'
        p = call(['rebuild', first_root, last_root, rebuilt, *inputs])
        assert rebuilt.read_bytes() == (LIVE / 'reconcile/state.bin').read_bytes()
        assert json.loads(p.stdout)['accounting']['reserve_principal'] == 600_000_000
        # These are relation/root failures, not missing executables or timeouts.
        for name, files in [('omitted', inputs[:-1]), ('reordered', inputs[::-1]), ('duplicate', [inputs[0], *inputs])]:
            p = call(['rebuild', first_root, last_root, t / name, *files], False)
            assert any(x in p.stderr for x in ['history discontinuity', 'final accepted root']), p.stderr
            assert not (t / name).exists()
        p = call(['rebuild', first_root, '00' * 32, t / 'wrong-root', *inputs], False)
        assert 'final accepted root' in p.stderr
        # Fresh unrelated wallet: the test driver never opens either secret file.
        user = t / 'new-user'
        call(['init', user])
        receive = json.loads((user / 'receive.json').read_text())
        assert set(receive) == {'schema', 'domain', 'owner', 'incoming'}, 'receiving data must not disclose native payout keys'
        assert receive['schema'] == 'KPI_USER_RECEIVE_V1'
        assert (user.stat().st_mode & 0o777) == 0o700
        assert ((user / 'wallet.backup').stat().st_mode & 0o777) == 0o600
        call(['init', user], False)
        scan = json.loads(call(['scan', rebuilt, last_root, user]).stdout)
        assert scan['notes'] == 0 and scan['spendableSompi'] == 0
        p = call(['exit', rebuilt, last_root, user, t / 'no-parameters-needed', t / 'unauthorized'], False)
        assert 'current recovered note' in p.stderr
        assert not (t / 'unauthorized').exists()
        p = call(['scan', rebuilt, '00' * 32, user], False)
        assert 'expected accepted state root' in p.stderr
        # Mutate one public state byte, keeping the original independent root.
        bad = t / 'changed-state.bin'
        b = bytearray(rebuilt.read_bytes()); b[0] ^= 1; bad.write_bytes(b)
        p = call(['scan', bad, last_root, user], False)
        assert 'expected accepted state root' in p.stderr
        bad.write_bytes(rebuilt.read_bytes() + b'\0')
        call(['scan', bad, last_root, user], False)
        # Truncated history is malformed input, never an accepted replay.
        bad.write_bytes(inputs[0].read_bytes()[:20])
        call(['rebuild', first_root, last_root, t / 'truncated', bad], False)
        (user / 'wallet.backup').chmod(0o644)
        p = call(['scan', rebuilt, last_root, user], False)
        assert 'regular 0600' in p.stderr
        print(json.dumps({
            'scope': 'OFFLINE_RETAINED_ACTUAL_TN10_HISTORY_REPLAY_AND_CLI_CONTROLS',
            'actualHistoryBatchesReplayed': 4,
            'exactStateSha256': hashlib.sha256(rebuilt.read_bytes()).hexdigest(),
            'stateRoot': last_root,
            'negativeControls': ['omitted batch', 'reordered history', 'duplicate batch', 'wrong independent root',
                                 'init overwrite', 'unrelated wallet exit', 'scan wrong root', 'changed state',
                                 'trailing state bytes', 'truncated input', 'public backup permissions'],
            'unrelatedWalletBalance': 0,
            'sharedReceiveFields': sorted(receive),
            'newOuterProofs': 0, 'rpc': False, 'providerActions': False,
            'independentCustodyEstablished': False,
        }, indent=2))

if __name__ == '__main__':
    main()
