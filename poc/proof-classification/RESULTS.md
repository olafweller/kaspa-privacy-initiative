# Local classification findings — 2026-10-17

**Outcome: correct guest execution, but a substantial proof-cost blocker.**
The small valid-invalid-valid sequence executed with outcomes `[0, 3, 0]` and
proxy balances `[600000000, 600000000, 500000000]` from one billion integer units.
The middle operation contains an actually corrupted submitted wallet seal. All
three operations remain bound to the same fixed ordered native-ID fixture.

Two real RISC Zero wallet receipts were generated and SDK-verified with no
development mode. **No outer classification receipt was produced.** The complete
execution needs **870,829,938 user cycles**, **880 segments** and **921,960,448
padded cycles**. This is materially different from PR35's cheap recursive
assumption call. Guest execution is evidence about the tested code; it is not
a cryptographic proof of the resulting classification journal.

## Actual measurements

| Measurement | Observed result | Scope |
| --- | ---: | --- |
| Complete sequence execution | 13.95 seconds; 870,829,938 user cycles | Executor only; not proving time. |
| Same-size encoding-rejection baseline | 0.57 seconds; 19,046,092 user cycles | Same native shell/payload sizes, receipt tags made invalid before SDK decoding/verifying. |
| Difference from that baseline | 851,783,846 user cycles | SDK receipt decoding, canonical binding and actual three seal checks; not a pure isolated verifier measurement. |
| Wallet proof A | 87.06 seconds; 100,574 user cycles | Real succinct proof of the small preimage/sum relation. |
| Wallet proof C | 88.88 seconds; 100,574 user cycles | Separate real wallet receipt, same relation. |
| Main sequence peak process RSS | 72,492 KiB | Execution, not outer proving memory. |
| Two-wallet run peak process RSS | 1,460,008 KiB | Maximum individual process, not sum of concurrent processes. |

The initial 268,435,456-cycle profile ceiling was reached. Raising it to
4,294,967,296 cycles allowed the entire sequence to complete. The earlier limit
is not evidence of impossibility. The 880-segment result is the concrete reason
not to launch an unbounded CPU proving job for this package. Full outer proving
time/memory were **not measured**, and no hardware-independent impossibility or
production throughput claim follows. Three real wallet receipts were generated
in total: two in the retained complete fixture and one earlier diagnostic run.

## Native payload calculation

Each complete proxy operation contains a 570-byte canonical intent, four-byte
proof length and 223,418-byte SDK receipt: **223,992 bytes**. Its native shell
has one dummy input with a 65-byte signature placeholder, declared v1 compute
budget 100 and one 34-byte P2PK output. The native SDK reports:

- estimated native serialized bytes: **224,257**;
- compute mass: **234,617**, against pinned block limit 500,000;
- transient mass: **897,028**, against pinned block limit 1,000,000.

One operation consumes about **89.7% of a whole block's transient capacity**;
two such operations cannot share a block under those parameters. This is a
local dimension calculation, not a relay/admission or fee test. Storage mass,
authenticated input value/age, actual signatures, coinbase/other block contents
and final private/vProgs metadata are not qualified. The opaque delivery records
are exactly two 128-byte synthetic blobs, not a chosen complete note encoding.
The three-item fixture spans an ordered sequence, not one asserted native block.

The initially used legacy input constructor gave a sigop-count commit instead
of v1 compute budget; mass calculation correctly aborted. It was corrected to
the explicit v1 constructor, and the already verified wallet receipts were
reused in a fresh fixture. No receipt was silently regenerated or relabelled.

## Negative controls and enforcing boundary

The guest actually checks the full canonical submitted receipt, not an optional
local assumption. Withheld, replaced, omitted or reordered bytes against the
same fixture commitment abort authentication. A trailing host verdict is not
part of the input format and aborts. These are execution failures, not proven
on-chain rejections. A replayed valid intent gets outcome 4 without changing
the counter a second time. This is finite-batch proxy replay handling, not
cross-batch economic note/nullifier consumption.

Malformed submitted receipts are exercised between the two genuine valid
operations: empty, truncated, fake tag, oversized declared seal length, all-zero
bytes, unreduced field/path words, out-of-range path index/exponent, short seal,
wrong journal and a proof one byte beyond the permitted profile. These get
outcome 2 and preserve the middle balance, while the following valid operation
continues. Additional host tests cover 64 mutations through the real seal,
eight truncations and 14 intent-binding mutations. CI adds three parser/domain
tests, including 256 deterministic arbitrary-encoding vectors. These checks do
not constitute a totality proof or independent cryptographic audit.

Post-review harness correction: authentication controls now require the exact
expected guest assertion category, including the dedicated trailing-input check
for a host verdict. Session limits, memory/IPC failures and unrelated guest
panics fail the test instead of being counted as authentication success. The
five real negative executions were repeated with this stronger check and are
retained in [expected-abort-review.json](evidence/expected-abort-review.json).

The main cost fixture's corrupt middle receipt shares intent A with the first
operation; the explicit outcome 3 is checked before replay handling. An additional
`invalid-unspent` control isolates that condition: corrupt C appears while its
intent is still unconsumed, then genuine C succeeds. It also returns `[0, 3, 0]`
with the unchanged middle balance. Neither invalid-proof processing nor later
acceptance is inferred merely from a replay rejection.

## What remains blocked

The practical requirement is still a **proved**, affordable processing path tied
to actual accepted Kaspa lane ordering. This prototype has a fixed local fixture
commitment, real native v1 hashing and an executed classifier, not a new TN10
acceptance/settlement proof. Its local domain, three-item bound and 4,096-byte
rest-preimage profile are not a general accepted-lane implementation. Missing
source data halts; no data-availability guarantee has been introduced.

Do not build the complete privacy circuit around this unqualified classifier.
The next bounded comparison should use the already identified specialized
BN254/Groth16 wallet route with an ordinary in-guest verifier, against the same
intent/order/malformed-input requirements. It remains unimplemented/unmeasured;
smaller encoding alone establishes neither faster in-guest verification nor
acceptable setup/VK/licensing/wallet assumptions. Reworking admission or using
a different verifier still needs a completeness/censorship/availability argument.

No proof system is selected for production, no privacy/payment milestone is
claimed, and no TN10 broadcast, funded output, key or service was touched. The
conditional TN10 proposal remains **not ready for funding**.
