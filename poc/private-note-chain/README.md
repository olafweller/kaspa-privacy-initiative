# Private-note state/native integration calibration

This package integrates real private-note wallet verification with atomic state
updates, native transaction preimages, lane commitments and a 352-byte native
aggregate journal in a new monolithic RISC Zero guest. **It is execution-only
research: no new outer receipt, native script acceptance, TN10 broadcast or GPU
rental.** See [results](RESULTS.md), [declared plan](PLAN.md),
[bindings](BINDINGS.md), [adversarial review](ADVERSARIAL-REVIEW.md) and
[GPU decision](GPU-PROPOSAL.md).

The fixed unfunded TN10 rehearsal domain is in [domain.json](domain.json).
PR44's default LOCAL-NO-FUNDING circuit/artifacts remain unchanged as a baseline;
`tn10-rehearsal` selects a different economic domain and requires this new VK.
The new setup is experimental one-party Groth16, not a production ceremony.
The new guest contains only public operations/state and checked proof verification;
wallet keys, openings and paths are not guest inputs.

## Reproduce archived public checks

From the repository root with the retained Rust 1.91.0 environment:

```sh
cargo +1.91.0 test --locked --release --manifest-path poc/private-note-chain/Cargo.toml -- --test-threads=1
cargo +1.91.0 test --locked --release --manifest-path poc/private-note-wallet/Cargo.toml -- --test-threads=1
```

These replay actual archived proofs, eighteen native-reference scenarios and
input mutations without a setup, wallet secret, provider credential or proving
job. Five chain tests and all nine PR44 regression tests pass. To rerun guest
execution only, use the exact pinned r0vm and program:

```sh
python3 poc/private-note-chain/run_qualification.py --r0vm /path/to/pinned/r0vm --host .local/ci-target/release/kpi-private-note-chain-host --program poc/private-note-chain/evidence/guest.program.bin --fixtures poc/private-note-chain/evidence/public --out /path/to/new-output-directory
```

The runner stops at the recorded 128M full-sequence failure; it does not enlarge
the budget. The program/image and r0vm are checked before execution. Build details
and all identities are in [evidence/identities.json](evidence/identities.json).
The guest rebuild was byte-identical. The monolithic guest's transaction/batch
slots are relation-domain constants, not newly produced recursive guest images.

## New local wallet generation and recovery

The host supports `generate NEW_PRIVATE_LOCAL_DIR`, followed by
`prepare THAT_DIR NEW_PUBLIC_FIXTURE_DIR`. This creates a fresh setup and wallet
proofs; a different VK requires new pins/build/qualification and does not reproduce
the archived identity. Files are created exclusively; local secret backup mode
is 0600 inside a 0700 directory. **Never copy the generation directory wholesale
into Git or an outer proving job.** Only whitelisted public artifacts are retained
in this package. The generation's initial wallet-check cases are not the linked
native fixture set; `prepare` constructs and checks that set separately.

`restore PRIVATE_LOCAL_DIR EXPECTED_VK_HEX` starts an independent local wallet
process. It loads the retained public parameters and Bob's own newly generated
synthetic backup, discovers his note from accepted public records and produces a
fresh exit proof. This succeeded without Alice's wallet secrets. It is not a
second-machine recovery or durable public archive qualification. The public
parameters remain in ignored local storage, identified by SHA256; no secrets
were copied to B or a remote prover.

`build_guest.sh NEW_PROGRAM_DIR` builds with the existing custom RISC Zero toolchain,
wraps the ELF using the retained host utility and verifies the compiled key's
identity. It cannot rent infrastructure, broadcast a transaction or produce a proof.
