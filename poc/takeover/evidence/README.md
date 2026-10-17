# Local recursive review evidence

See the [review](../LOCAL-REVIEW.md), [machine-readable result](local-review.json)
and [artifact archive](local-review-artifacts.tar.gz). The JSON records the
archive's SHA-256 and size, the exact reviewed source commit, 50 source/manifest/
lock hashes, compiler and host/prover identities, program hashes, proof reports,
execution rejections and measured resource use.

The archive contains rebuilt raw/wrapped programs, actual prepared inputs,
receipts, committed journals, execution profiles/reports, precise missing/wrong
receipt and expiry failures, the source snapshot and selected verification/build
failure logs. `manifest.json` hashes each other member. It does not contain wallet
keys. The exact executed host binary is retained in the separate downloadable
handoff archive, with its hash in the source snapshot.

All chain data comes from the existing PR32 public captures, which remain in
`poc/native-value/evidence`. Combining the two contiguous intervals is a
reproducible derivative, not a new node observation. The historical withdrawal
was already paid in PR32. This review makes no new payout, privacy, production
security, independent-operator or long-gap TN10 claim.

To inspect integrity without executing any archived program, from repository root:

```python
import hashlib, json, tarfile
from pathlib import Path
root = Path('poc/takeover/evidence')
report = json.loads((root / 'local-review.json').read_text())
archive = root / report['artifactArchive']['path']
assert hashlib.sha256(archive.read_bytes()).hexdigest() == report['artifactArchive']['sha256']
with tarfile.open(archive) as t:
    manifest = json.load(t.extractfile('manifest.json'))
    for name, expected in manifest.items():
        raw = t.extractfile(name).read()
        assert len(raw) == expected['bytes']
        assert hashlib.sha256(raw).hexdigest() == expected['sha256']
print('Artifact hashes match; this is an integrity check, not a security audit.')
```

Repeat build/preparation/proof commands are in the [adapter README](../README.md).
No automated command in this evidence sends TN10 transactions.
