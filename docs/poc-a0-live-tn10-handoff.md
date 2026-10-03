# A0.5 handoff: live TN10 reserve-release validation

**Scope:** continue A0 on TN10; do not start A1. Candidate A is experimental,
ADR-0001 is Proposed, and A0 is not complete. No live TN10 evidence exists yet.

Repository: `olafweller/kaspa-privacy-initiative`.
Branch: `poc-a0-reserve-release`, targeting `main` through a draft PR.
Continue [draft PR #20](https://github.com/olafweller/kaspa-privacy-initiative/pull/20).

## Start locally

In an existing clone with a clean working tree:

```bash
git fetch origin
git switch --track origin/poc-a0-reserve-release
rustup toolchain install 1.91.0 --profile minimal
./scripts/run_poc_a0.sh
./scripts/run_poc_a0.sh test
python3 scripts/check_docs.py
```

If the local branch already exists, use `git switch poc-a0-reserve-release` and
`git pull --ff-only`. Review local changes before switching; do not reset them.
The reproduced baseline is 28 rejected variants, one valid fixture, one expected
stateless-replay acceptance, and four passing circuit tests.

Use Linux (or a Linux environment) with Git, rustup, C/C++ build tools, libclang,
OpenSSL headers and pkg-config. Debian/Ubuntu package names are
`build-essential libclang-dev libssl-dev pkg-config`. Allow several GiB of disk
and substantial memory for the RocksDB/consensus build. The measured cloud VM
had a 16 GiB limit. Other host platforms have not been validated.

The runner pins Rust 1.91.0 and Rusty Kaspa v2.1.0 revision
`01b532e8b553523216471682649693af92f0fd16`, with a clean source checkout at
`../upstream/rusty-kaspa` relative to the KPI root. Registry versions/checksums
are in `poc/a0/Cargo.lock`. Preserve these pins or separately document and review
any version change. No RPC environment-variable contract is implemented yet.

Read [A0 results](poc-a0.md), [the statement/encoding](poc-a0-proof.md),
[upstream boundaries](poc-a0-upstream.md), and [ADR-0002](adr/0002-a0-reserve-release-experiment.md).
Implementation entry points are `poc/a0/src/main.rs` (`policy`, `redeem`,
`signature`, `validate`) and `poc/a0/src/circuit.rs` (`ClaimCircuit`, `compute_tag`,
`public_inputs`). `poc/a0/evidence/` contains sanitized local measurements.

## Minimum next action: prepare the missing adapter before funding

Implement and review a small **TN10-only** deployment/proving/RPC adapter using
the existing covenant and circuit. The current executable cannot resume, fund,
query UTXOs, broadcast, or observe acceptance. It generates a random outpoint,
uses fixture DAA context, and discards setup/witness material. Its recipient
private key is discarded inside `policy()` itself. **Never fund its ephemeral
P2SH script or reuse its synthetic outpoint.**

The adapter must first retain, outside Git and with restricted permissions:
the randomly generated claim secret; immutable claim/domain/state terms;
the same proving key and verifying key; exact redeem/P2SH bytes; and access to
a test-only recipient wallet/key. Verify backup/reload produces the identical
verification key, context and locking script before funding. Retain the proving
key for proving; do not retain setup randomness/toxic waste as a recovery tool.
Local single-party setup remains trusted and is suitable only for this test.

Use a recipient that the local operator can actually spend from. A recipient
address must be decoded to the exact standard P2PK script and its version;
do not substitute a different destination after setup. The encoding checked by
`OpTxOutputSpk` is big-endian u16 version followed by script bytes.

Before any test funding, verify all of the following:

- The connected, synchronized node reports `testnet-10`; independently verify
  its genesis against the pinned TN10 parameters. An address prefix alone is
  insufficient to distinguish testnets. Fail closed for mainnet or ambiguity.
- Record node version/revision, sync status, current DAA context, and RPC schema.
  Confirm support for transaction version 1, input compute budgets, storage mass,
  and output covenant fields. Do not silently downgrade serialization.
- Use only faucet/test KAS and a dedicated test wallet, never a mainnet seed.
- Generate a fresh claim/state ID and secret. Fix the protocol label, TN10
  genesis, state ID, recipient, R/A/F amounts and terminal marker **before setup**.
  Setup is circuit-specific but independent of the future funding outpoint.
- Reuse the existing terminal policy: one reserve input, one payout output,
  payout `covenant=None`, no successor. Baseline R/A/F is 10.2/10/0.2 test KAS.
  F is a separate fee buffer, not an extra user liability.
- Check current relay policy and budgets before funding. This covenant cannot
  add a sponsor input, change output, or reduce payout to bump fees. A different
  fee/amount/recipient requires changed constants, setup and script **before**
  funding, plus new tests. Never weaken output checks to make a spend relay.
- Reproduce full local validation of the adapter's exact serialization, retain
  all required data, and verify the funded output will have the intended P2SH
  bytes, exact amount R, and no covenant ID. Funding-transaction change is
  separate from the later one-input/one-output reserve spend.

## Derive proof inputs from the actual funded reserve

After the funding transaction is accepted, locate its reserve output by exact
script and value, then query the node's UTXO view. Do not assume output index 0
or the fixture's index 7. Record the actual funding transaction ID, output index,
amount, script version/bytes, covenant metadata, coinbase flag and DAA data.
Check the UTXO is still unspent immediately before constructing the release.

Retain the **original** setup/key and immutable context. Do not run `main()` or
regenerate setup after funding: a different verification key changes the P2SH
conditions and cannot unlock that output.

Recompute with the actual outpoint, using the upstream `Hash::as_bytes()` byte
representation rather than guessing display-hex endianness:

```text
T = SHA256(context_prefix || secret32 || funded_txid32 || funded_index_LE32)
public inputs, in verifier order:
  0: funded_txid bytes 0..16 as LE128
  1: funded_txid bytes 16..32 as LE128
  2: funded_index as unsigned 32-bit integer
  3: T bytes 0..16 as LE128
  4: T bytes 16..32 as LE128
```

Generate a fresh proof under the original proving key. Canonically serialize
each scalar in 32 bytes, and proof/VK with pinned arkworks compression. The
spending signature script supplies tag-high, tag-low and proof; the redeem
script derives the outpoint fields itself through introspection. Do not supply
a trusted external verifier result. Populate local validation with the actual
UTXO and current node context, calculate mass, preserve the budget, and verify
the exact recipient output and R = A + F accounting before submitting.

The domain constant is not a consensus chain-identity oracle. Identical copied
state/rules on a fork remain outside A0's cross-chain replay claim. Fresh state
IDs separate these single-claim deployments; there is no general pool namespace
or multi-user state tree in A0. No reserve continuation is permitted because the
single liability is fully paid atomically.

## Broadcast, observe, and test replay

Before spending the valid reserve, submit applicable invalid variants that have
already failed locally. Record raw sanitized RPC responses, node state and
transaction identity for each. Restore the intended valid spend afterward.
If an unexpected variant is accepted, stop, preserve evidence and investigate;
do not keep testing as though the reserve were still available. Network policy
errors, timeouts, and rate limits do not establish consensus rejection.

For the valid release, record submission response/transaction ID, exact public
transaction and proof data, observed block/acceptance information, DAA score and
the chosen confirmation/observation policy. Kaspa block inclusion alone is not
enough: verify transaction acceptance, reserve UTXO disappearance and creation of
the exact recipient UTXO/value. Recheck after the observation window; handle
reorgs explicitly. Do not call the transaction permanently final from one RPC.

For exact replay, resubmit the identical serialized transaction after accepted
settlement. A node may return an idempotent/already-known response; that alone
is neither a second payout nor proof of a spent-input rejection. Query the
reserve and recipient UTXOs and confirm there is no second payment. Also create
a distinct transaction spending the same outpoint while preserving valid proof
and payout conditions (for example change input sequence from `u64::MAX` to
`u64::MAX - 1`, preserving the relative-lock disable bit). Sequence is included
in the transaction ID but not this proof relation. First show the variant passes local
validation against the original UTXO, then submit it after consumption. Record
the actual spent/missing-input rejection. If relay policy rejects it for another
reason, report that limitation; do not label it a live double-spend test.

Proof reuse against another funded outpoint is a separate test: it must fail
Groth16 verification because introspection changes the proof inputs. Do not
infer this result from exact-replay behavior. State/domain/key substitutions
and economic/output mutations remain distinct checks from UTXO spentness.

## Evidence to add to this draft PR

Add reviewed adapter code and reproduction commands, exact dependency/node
versions, network/genesis checks, funding/release txids and output indexes,
public transaction/proof/VK/redeem encodings, mass/fee measurements, timestamped
acceptance and UTXO observations, all applicable negative-test responses, and
replay/reorg limitations. Keep local and live evidence in separate files. Update
the A0 report only for observations actually obtained. Do not accept ADR-0001,
select Candidate A, or claim anonymous/private-accounting/recovery functionality.

Never commit `.env`, seed phrases, wallet/recipient private keys, the claim
secret, prover witness dumps, setup randomness/toxic waste, credentials, RPC
tokens, credential-bearing endpoint URLs, private local paths, or raw debug logs
containing them. Keep proving material/backups outside the repository too.
Public proofs and verification data still require a deliberate sanitization
review; a filename being Git-ignored is not sufficient protection.

## Publication links

- [Draft PR #20 — PoC A0: real-proof reserve-release feasibility spike](https://github.com/olafweller/kaspa-privacy-initiative/pull/20)
- [Feature branch](https://github.com/olafweller/kaspa-privacy-initiative/tree/poc-a0-reserve-release)
- [PQ tracking issue #19](https://github.com/olafweller/kaspa-privacy-initiative/issues/19)

Push reviewed A0.5 work to this feature branch to extend the same draft PR.
Do not merge it or begin A1 as part of the live-validation handoff.
