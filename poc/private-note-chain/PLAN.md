# Declared execution calibration — before first guest run

Date: 2026-10-18. Local CPU only, no proof job, provider operation or transaction.

- Wallet domain: exact `domain.json`; new key is independently pinned in `pins/`.
- Expected guest image: `20d8431e18f42c6e337ab726f166914516e3ebcd70577e67d49e687737901f8b`.
- Pinned RISC Zero SDK/r0vm 3.0.3 and v1compat 2.2.2, original backend commit.
- Exactly 128,000,000 user cycles and 900s process-group wall time per scenario.
- Four CPU affinity slots and four Rayon/BLAS/OpenMP threads. No address-space
  limit; record actual RSS and the environment's memory limit.
- First measure deposit, credit, transfer and exit separately, then the four
  prior-state/config/lane/start authentication aborts, native-output controls,
  cross-batch competing/replay/recovery controls, malformed/invalid continuation
  and finally the complete valid-invalid-valid three-proof sequence.
- Every completed journal must equal the independently computed 352-byte native
  aggregate journal. Full state/events/reference transaction journals are retained
  as public expected evidence; they are not extra bytes in the native receipt ABI.
- Enable dynamic pprof only on credit to establish accelerated execution; do not
  infer acceleration or compatibility merely from dependency inclusion.
- A correctly matched guest authentication assertion is a passed control; cycle,
  wall-time, memory, IPC and unrelated assertion failures are failed runs.
- Stop the qualification on the first unexpected/resource failure, retain its
  last log stage and mark subsequent cases unexecuted. Do not retry or raise the
  cap. Separate transaction measurements do not redefine a failed full sequence.

This monolithic execution calibration computes native v1 IDs and lane endpoints
from serialized transaction preimages, checks deposit outputs and current state,
and emits permission commitments. Anchors are local synthetic fixtures, not
observed canonical TN10 facts. It is not a real outer receipt, recursive
transaction/batch/aggregate proof or native script acceptance/payout. Those must
be supplied and tested before any funding. A permission commitment is an unpaid
exit obligation, never evidence of its native payout or release of reserve.
