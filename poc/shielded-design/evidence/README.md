# Local model and real composition evidence

- [model-cycle.json](model-cycle.json): simulated Alice/Bob principal lifecycle
  and separate permission-rent funding; not a chain payout or cryptographic test.
- [source-review.json](source-review.json): dated upstream refs, selected file
  hashes, bounded retrieval failures and code-rights boundary. Restricted source
  files are not redistributed.
- [compatibility.json](compatibility.json): four-proof local chain, isolated
  repeated wallet measurement, actual abort errors, matched execution cycles,
  exact source/program/prover hashes and explicit blockers.
- [local-compatibility-artifacts.tar.gz](local-compatibility-artifacts.tar.gz):
  real receipts, journals, profiles, rejection errors, public prepared reference
  input, reference/compatibility programs, exact source snapshots and logs.

The first four-proof host source snapshot is frozen separately from the later
host that adds an isolated wallet/profile measurement command. Both content-hash
maps are retained; no earlier run is attributed to the later source bytes.
Synthetic preimages and deterministic wallet keys are public test fixtures.
No real signing key, secret environment or restricted third-party circuit source
is included. Native script checks use a local accessor; there was no new native
submission, private payment, independent operator or anonymity measurement.

Integrity check from repository root, without executing any archive member:

```python
from pathlib import Path
import hashlib, json, tarfile
root = Path('poc/shielded-design/evidence')
result = json.loads((root / 'compatibility.json').read_text())
archive = root / result['artifactArchive']['path']
assert archive.stat().st_size == result['artifactArchive']['bytes']
assert hashlib.sha256(archive.read_bytes()).hexdigest() == result['artifactArchive']['sha256']
with tarfile.open(archive) as t:
    manifest = json.load(t.extractfile('manifest.json'))
    assert set(t.getnames()) == set(manifest) | {'manifest.json'}
    for name, expected in manifest.items():
        raw = t.extractfile(name).read()
        assert len(raw) == expected['bytes']
        assert hashlib.sha256(raw).hexdigest() == expected['sha256']
print('Integrity checked; this is not a cryptographic audit.')
```
