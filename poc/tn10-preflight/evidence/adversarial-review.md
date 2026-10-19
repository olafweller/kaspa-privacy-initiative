# Focused preflight self-review

No monetary relation, native script, guest or GPU image changes. The new numeric
RPC client reuses the reviewed read-only method/endpoint allowlist; mutation and
another endpoint are rejected before connecting. Raw u64 responses remain exact.
This is an implementation self-review, not a new independent Astra review.

No transaction was signed/submitted, proof generated or lease created. Existing
balances are snapshots, not spending authority or a future spentness guarantee.
Every actual spend still needs fresh chain/outpoint/anchor/native checks; stale
or reorged snapshots cannot stand in for future checkpoints. Test-KAS principal,
state rent, permission rent and fees remain separate.

Only public files and retained proof bytes were installed/copied. Role files
were checked with stat; secrets were not opened or transferred. B root/operator
and the one native node remain trusted. Bob custody was unresolved at the host preflight. The owner subsequently
confirmed existing-operator custody for this test; see `custody-decision.json`.
This does not establish independent user custody or malicious-operator isolation.
Systemd supplied the existing B account credential to a bounded read-only quote
process without exposing it to the controller, argv, repository or GPU.

B's existing guard code/unit were preserved and inactive, with the old lease
left intact. A fresh real lease must replace the binding before any activation.
Host recovery/controls were simulated; actual stop/write permission and CUDA
execution were not exercised in this preflight. The existing independent guard
must still stop rental if Cloud/gateway/operator disappears during a future run.
The quote is observed availability/pricing, not a reservation or bill cap.
