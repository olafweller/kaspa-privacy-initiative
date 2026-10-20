# Run checklist — not a rental/proof release

1. Check the final deployment digest, trusted archive/binary/source bindings and
   service scope `FIXED_RECOVERY_SIX_SUCCINCT_RECEIPTS`. Restore the package on B
   into a fresh directory and run `check-target` for all six cases plus
   `check-native-context`. Retain the existing B installation and historical data.
   Install every `trustedBClientFiles` entry from the runmanifest together in the
   client directory, including `staged_archive.py`, and verify those hashes.
   `recovery_control.py extract` requires that bounded archive helper. Run its
   actual CLI smoke test from the installed directory before receiving results.
2. At a separately released run, check B's NTP clock, storage, installed guard and
   current GPU/storage quote against the USD5 planning allowance. Use only B's
   existing root-only credentials, never print or transfer their values.
3. Allocate exactly one L40S with the immutable image. Read back actual resources,
   quote, creation time and image digest. Bind a new lease to that creation time
   with `stopUnix <= createdUnix + 7200`; never reuse an earlier trial lease.
4. Configure the HTTPS service through B with its existing service token. Read
   back exact scope, idle/fresh attempt state and lease binding. Arm B's independent
   guard and require a fresh heartbeat. B must enforce backup/stop without Cloud,
   gateway or laptop. Keep storage until its external evidence copy is verified.
5. Require more than 3960 seconds to the absolute lease deadline before starting.
   B begins stopping 60 seconds before that deadline. Start promptly on a fresh
   two-hour lease; do not extend it. The fixed runner produces six receipts in
   order, separately verifies each and checks both genuine native exits, under
   one external 3600-second timer. No automatic retry or extra workload.
6. Preserve artifacts through the existing authenticated artifact endpoint and B
   guard. Safely extract using `recovery_control.py extract ARCHIVE NEW_DIR SHA256`.
   Use `recovery_control.py verify TRUSTED_PACKAGE EXTRACTED NEW_VERIFICATION` on
   B and again on trusted CPU if desired. Use binaries only from the trusted
   package. Partial/candidate results are retained and explicitly labelled.
   The B extractor bounds compressed reads and the whole gzip expansion before
   tar parsing, including hidden PAX/GNU headers and padding. The received hash
   alone does not provide an expansion bound.
7. Require six final cryptographically verified receipts, both genuine native
   permission/payout checks, per-batch matching-process CUDA activity and complete
   timing/RAM/VRAM records for full success. Preserve all diagnostics on failure.
8. On every outcome confirm provider EXITED using B's existing guard/provider
   route. After durable external archive/hash and CPU verification, delete only
   this attempt's Pod/chargeable storage and confirm absence/404. Record actual
   rental duration, rates and costs; distinguish estimates from a final invoice.

This phase performs no steps 2–8. Native funding, broadcasts and public chain
acceptance are outside this local proof qualification.
