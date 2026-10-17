# Recursive review and TN10 evidence

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

## Fresh live TN10 evidence

The subsequent [confirmed rehearsal](../LIVE-REHEARSAL.md) has a separate
[verified result](tn10-rehearsal.json) and [archive](tn10-rehearsal-artifacts.tar.gz).
Use the same integrity code above with `tn10-rehearsal.json`. It retains all 89
public VPS files in `vps-public.tar.gz` with a second per-file manifest, eight
real proof receipts and journals, prepared inputs, clean replay, measured proof
resources, program/source hashes and audit logs, including the corrected
read-only accounting failure. Wallet keys are outside the public trial and
are not included. Local host proof reports remain separate from actual native
acceptance records. The live report states the exact same-owner/node scope.

## Final review replay

The separate [final-review.json](final-review.json) records read-only SDK
re-verification of all eight live receipts, eight changed-journal and eight
wrong-program rejections, independent Python native-order/state/accounting checks,
the repeated PR32 audit and review-tool hashes. Original evidence archives are
unchanged. [Reproduction commands](../FINAL-REVIEW.md) need no keys, RPC or prover.
This is additional verification of recorded observations, not another independent
node/operator or new on-chain test.
