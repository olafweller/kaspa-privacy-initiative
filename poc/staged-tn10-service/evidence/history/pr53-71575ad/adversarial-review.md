# Adversarial second pass — 2026-10-19

This is an implementation self-review, not an independent Astra review or a
cryptographic audit. No new proof/GPU/provider/chain action was performed.

- Inflation, double-spend and unauthorized reserve release: the host, guest,
  wallet relation and native restrictions are unchanged. Transport cannot make
  a new executable or returned expectation trusted. B approves target bytes;
  the separate CPU verifier uses its installed executable and independent target.
  Actual native settlement/UTXO acceptance remains mandatory in the later trial.
- Replay/concurrency: targets are immutable, stage order/root/tip continuity use
  the reviewed reserve ledger, and an accepted stage is consumed durably before
  spawning. Identical lost-response re-uploads are idempotent, not a second job.
  A lifetime volume flock prevents another mutating service process.
- Process loss: restart first durably closes the launch gate, then kills only a
  matching registered process group (boot ID/start ticks prevent PID confusion).
  The child registers before checking the gate, closing the launch/restart race.
  Waiting restarts preserve the deadline and require a new B heartbeat.
- Dependency disappearance: the external GNU timeout bounds each remaining
  process group; one absolute aggregate ledger deadline includes all waits.
  Unchanged independent B supervision retains the absolute rental stop even
  when service I/O or archive transfer fails. Actual provider stop is untested.
- Privacy leakage: image and uploads contain public program/trial/input/journal
  only. No secret files are read or packaged. The service token is in its
  environment, never the archive/state/logs. B root remains trusted; transport
  authentication does not hide data from administrators or establish production
  financial privacy.
- Reorg/stale state: service continuity cannot establish actual selected-chain
  freshness. The reviewed capture/checkpoint/preflight workflow still must
  authenticate actual inputs and abort on stale state or reorg before release.
- Evidence: candidates and completed stages survive a later failure. A failed
  subprocess/resource timeout is not a successful crypto rejection. External
  CPU verification checks real receipt bytes; synthetic producer/provider tests
  remain explicitly distinct from actual CUDA and provider qualification.

Retained regression fixtures have old chain context. They do not establish
receipts, anchors, recipients or outpoints for the fresh TN10 trial. The concrete
remaining live gates are listed in the supplemental run manifest.
