# Retained local evidence

[classification.json](classification.json) records actual execution/proof scopes,
cycles, native masses, negative outcomes and exact source pins.
[local-classification-artifacts.tar.gz](local-classification-artifacts.tar.gz)
retains the two real wallet receipts, programs, canonical input fixtures, native
ID/order expectations, journals/profiles, resource logs, malformed controls and
exact source snapshots. Its internal manifest lists every member's size and
SHA-256. The JSON records the archive hash and byte size.

There is **no outer classification receipt** in the archive. No execution journal
is relabelled as a proof. Both the original cycle-limit failure and the completed
larger execution are retained. The first complete preparation generated both
wallet receipts but failed at mass reporting due to the legacy input constructor.
The corrected fresh fixture reverified and reused those same receipts, with
receipt hashes and source snapshots preserved.

An additional earlier diagnostic wallet receipt is accounted for in run history,
but is not part of the complete fixture. No credentials, real signing keys,
live wallet backups or restricted circuit sources are included. Synthetic wallet
witnesses are deliberately public reproduction fixtures.
