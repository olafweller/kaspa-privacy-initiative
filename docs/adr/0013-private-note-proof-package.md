# ADR-0013: fixed monolithic private-note proof and join-native preparation

Status: Software preparation completed and subsequently owner-reviewed/released,
2026-10-18. One bounded GPU attempt completed; the owner performed the Astra
review in Chat. The original preparation did not itself authorize rental.

## Observed follow-up

The [single released GPU result](../../poc/private-note-proof/gpu-2026-10-18/RESULTS.md)
produced the genuine frozen private-note Succinct receipt in 243.088 seconds.
Independent CPU and local native positive/fifteen-negative checks passed. B
preserved the archive; Cloud recovered and independently verified it. Provider
EXITED and subsequent deletion were confirmed. No guest, proof statement,
backing rule or TN10 transaction changed. The original decision and release
conditions below remain the historical basis; no additional attempt is implied.

## Decision

The completed 160M calibration fixes a 139,763,284-user-cycle, 143-segment target.
Prepare a fixed Succinct producer, independently built CPU verifier and local
native fixture using the unchanged guest/VK/proofs/input/352-byte journal.
Reuse the qualified RISC Zero 3.0.3 CUDA prover, remote fixed-job service and
independent B guard; add no wallet setup, new crypto or infrastructure service.

Unlike the prior assumption-composing route, this ordinary multi-segment guest
finishes with `join.zkr`. Add an explicit `SuccinctJoin` covenant variant and pin
the official Poseidon2 control identity. Leave existing resolve fixtures intact.
Require seal/metadata/expected-control equality and allowed-root inclusion in
addition to image, successful execution, no assumptions and exact journal checks.
Use the official STARK verifier callback, not new cryptographic arithmetic.

Keep the monolithic transaction/batch relation slots distinct from absent
separate recursive images. Native fixture backing is the full 1,000,000,000
sompi; it creates no exit and claims no canonical deposit, payout or fee/rent
acceptance. A real archived PR43 receipt may qualify join/precompile compatibility
but cannot substitute for the new private-note receipt.

## Evidence and later release

See [package and review boundaries](../../poc/private-note-proof/README.md),
[fixed target](../../poc/private-note-proof/target.json) and
[actual preparation results](../../poc/private-note-proof/RESULTS.md).

After owner review, a separately released single L40S attempt may retain the
existing <=3,600s full proof process and <=7,200s rental deadline, actual quote
and USD5 planning limit, independent B backup/stop and verified provider readback.
No repeated CPU calibration is needed. Incompatibility or resource failure keeps
the last completed stage; no retry, raised budget or weaker proof is automatic.
