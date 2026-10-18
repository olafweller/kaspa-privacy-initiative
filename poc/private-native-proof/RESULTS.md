# Four-batch proof-package preparation

PR49 was reviewed at `b44956e26d99b1f3bf74f7d9b3523788bb563c4f`, with all
eight required checks green, and squash-merged as
`08bd96d6a7ef647b09df7fb241ed164ff6e66b35`. This preparation leaves that guest,
wallet relation and native/accounting policy unchanged. No new outer proof,
rental, funding, provider mutation or TN10 transaction was performed.

## Immutable publication

- Image: `ghcr.io/olafweller/kaspa-privacy-initiative/cuda-qualification@sha256:aefe98f7e463ba3bbc4cc6b692cc739c04d083718983deb79b2543debb150db7`.
- Image source: `612e9f9a69aec67805e70b0fbca4ea3c757058da`.
- Public package SHA256: `f28dfcea27c8c357cece022b7036f013895d907a48b151c4e45d9700f3c2e5a0`.
- Workload SHA256: `f723def3f8da9fc63bb2bc08afadbb40745f2a7a3685885793b50b584ecf66fa`.
- Guest: `794cfff4cfa509799ec1f6750678d3fe4bc8623522aa647cc65e6b53955c4bc9`.
- Producer and verifier SHA256: `d9ee19513d2ba2b4296e0e9c4199c175ba2d0948b0f130d3df53a5e875415109`.
- Scope: `FIXED_PRIVATE_NATIVE_FOUR_SUCCINCT_RECEIPTS`.

The [publication workflow](https://github.com/olafweller/kaspa-privacy-initiative/actions/runs/39164252483)
built from the already qualified immutable CUDA base, checked the image on CPU,
pushed it, then pulled and checked the registry digest. Cloud independently
pulled that same digest and repeated the CPU checks. The final metadata commit
adds publication records and configuration; it changes no image runtime source.
The local Docker build ID is distinct from the registry digest.

See [publication provenance](evidence/publication.json),
[published-image CPU checks](evidence/published-container-smoke.json),
[package identity](evidence/package-identity.json) and the concrete
[run manifest](run-manifest.json). The manifest retains exact complete journals
and public-input hashes for `deposit`, `credit-transfer`, `exit`, `reconcile`.
The former PR47 image runs a different fixed workload and cannot substitute.

## Qualification and remaining experiment

All 28 credential-free orchestration/control tests passed, including seven new
lifecycle tests. The four compiled targets, complete journal continuity and
public archive/source/binary bindings passed. Real local process tests killed
a hung later descendant, retained earlier synthetic results, and established
that the external timeout survives controller loss. Those tests do not create
cryptographic receipts. Existing PR49 native/accounting evidence and PR48 proof
evidence remain intact.

CPU image checks verified package and CUDA-prover bytes, four compiled targets,
fixed service scope, fresh attempt state, authentication and rejection of an
unguarded start. The runtime NVIDIA driver is intentionally unavailable in this
CPU environment; no GPU activity, VRAM requirement or new proving time is claimed.

The future rehearsal has one aggregate 3,600-second process-group deadline for
all four proofs, compression and in-container CPU/native checks. No batch resets
the allowance. Partial/candidate receipts are retained. Independent B verification
uses the trusted package verifier and exact compiled expectations, including the
genuine new exit receipt's native permission issuance and restricted payout.
That genuine new receipt path remains unexecuted until the separately released
GPU attempt produces an exit receipt.

No B installation or lease was changed here. Before rental, independently check
B's clock/storage/guard, actual GPU plus storage quote, immutable image readback,
fixed service scope and fresh lease/attempt. Keep one L40S, one attempt and the
7,200-second creation-time rental limit. USD5 is a planning allowance, not a
guaranteed provider invoice cap. Retain B's independent backup and confirmed-stop
mechanism and require verified external preservation before deletion.

Even successful four-receipt/native-script checks use local synthetic UTXO and
anchor fixtures. Canonical TN10 acceptance, actual native payout, broader exit
shapes, multiple simultaneous exits, production privacy and security remain
outside this preparation result. Rental and proof execution require separate
owner release.
