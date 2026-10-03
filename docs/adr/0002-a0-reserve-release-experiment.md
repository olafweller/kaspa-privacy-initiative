# ADR-0002: A0 terminal reserve-release experiment

**Status:** Experimental scope decision; not a production architecture acceptance

**Date:** 2026-10-03

## Context and reconciliation

The requested A0 spike asks whether real proof verification can authorize native
KAS release through current Kaspa consensus. Repository research pins Rusty Kaspa
`01b532e8b553523216471682649693af92f0fd16`; this revision was fetched and inspected
again for A0. ADR-0001 remains **Proposed** and Candidate A remains experimental.

The existing PoC A and AGENTS.md describe a broader private-transfer and recovery
milestone. A0 is a preliminary sub-experiment and cannot satisfy that milestone.
The original source review had no real-proof TN10 round trip. A0.5 now records
that narrow terminal run in the linked evidence; source availability alone remains
insufficient to establish live endpoint acceptance.

CONTRIBUTING.md normally requests public coordination before substantial work.
The original task required local-only implementation and review. A subsequent
explicit instruction authorizes publishing this A0 feature branch, a draft PR,
and a PQ research tracking item, plus preparing the [A0.5 handoff](../poc-a0-live-tn10-handoff.md).
The subsequent local A0.5 instruction explicitly authorizes reviewed test-only
funding, broadcast and replay on this same draft PR. The observed result is in
[the live report](../poc-a0.md#a05-live-tn10-result). Merging and starting A1 remain
unauthorized.

## Experiment decision

Use the existing Groth16 BN254 verifier, fixed in a P2SH covenant, for a single
claim's terminal withdrawal. Use established SHA-256 preimage relations rather
than inventing notes, nullifiers, or a full privacy circuit. Bind the authorization
to the actual reserve outpoint and the exact transaction constraints. Fix the
verification key, owner commitment, protocol/domain, claim state, recipient,
amount, and explicit fee budget. No operator bypass or alternate withdrawal key.

For this terminal experiment, one reserve input pays one prescribed native-KAS
output. Let user liability be A and a separately funded experimental fee buffer
be F. The reserve is R = A + F. A valid terminal withdrawal pays A and consumes
F as the miner fee; remaining liability and reserve are zero. This is not a
general confidential accounting proof. No pending exit is created.

Use real upstream script and transaction validation where buildable, with TN10
parameters. Supplied local UTXO fixtures are not evidence of a funded reserve or
live consensus acceptance. Network execution requires a reachable TN10 node,
verified network identity, test-only funding, and observed transaction evidence.
Do not substitute a verifier mock or relaxed validation flags when blocked.

## A0.5 retained-key/native-RPC adapter, October 3

Continue the same circuit and P2SH authorization on draft PR #20, without
merging or starting A1. The supplied REST schema cannot preserve all A0 fields;
use the pinned official Node SDK and an own loopback TN10 node's native wRPC.
The file-only Rust adapter retains setup/claim material and calls the original
full validator. No proof, accounting, output or validation rule is relaxed.

Before reserve funding, validate a release from the exact signed funding output,
including an SDK roundtrip. After funding, read actual UTXO/context and generate
a fresh proof. Require accepted-chain and payout-UTXO evidence, a full accepted
transaction readback, spent-input replay rejection and a later recheck. A local
source/binary-hash review gate prevents accidental funding with changed tooling;
it is a test-run procedure, not an on-chain approval or withdrawal authority.

New operational assumptions are an uncompromised local host, accurate pinned
SDK/node artifacts, retained claim/proving and recipient material, and an explicit
blue-score-distance >20 observation window. A same-host backup is not disaster recovery. A0
remains transparent and terminal; no production finality/recovery rule or Candidate
A architecture is selected. See [runbook](../poc-a0-tn10-runbook.md) and
[report](../poc-a0.md#native-adapter-and-pre-funding-checks) for measured status.

### Native public RPC observation while local UTXO import is incomplete

The initial own-node bootstrap validated the TN10 pruning/header proof and
recent headers, but its UTXO import exceeded 50 million entries and is still in
progress. For this test, permit the two explicit TLS native-wRPC endpoints
resolved from upstream's public resolver infrastructure, after both report synced
TN10/2.1.0 and match independently rehashed recent headers from the own pinned
consensus process. The original actual genesis header must still rehash correctly,
and the local process/config identity must match the pre-pruning observation.

This changes the observation trust boundary, not the proof/covenant or accounting:
remote UTXO/acceptance data is trusted and corroborated across two endpoints, not
claimed to be locally UTXO-validated. Distinct endpoints are not proof of independent
operators. Local full validation of exact signed funding and reserve-release
transactions remains mandatory. After release, require the same accepted block
body, exact payout and absent reserve through both endpoints, plus later recheck.
Fail closed on disagreement. No experiment result establishes production finality,
remote-provider honesty, independent recovery or a general shielded state model.
The loopback-only full-node route remains preferable when already synchronized.

## Alternatives

- RISC Zero: supported upstream, but adds guest/receipt tooling for a statement
  that can be expressed directly with the available Groth16 verifier.
- Full shielded state: premature for the enforcement-boundary question; requires
  separately reviewed note, nullifier, conservation, discovery, and recovery rules.
- Based-app/vProgs settlement: useful reference, but unnecessary to test a direct
  inline verifier. Its development-mode paths do not establish proof soundness.
- Hashlock alone: does not test the requested real ZK verifier and exposes its
  authorization witness when spent.

## Assumptions and limits

Local Groth16 setup is experimental and trusted, not a reviewed ceremony.
SHA-256 preimage hardness, Groth16/BN254 soundness, correct circuit constraints,
canonical encoding, and correctness of the pinned consensus implementation are
assumptions. BN254/Groth16 is not post-quantum secure. Public reserve/payout values,
recipient, outpoint, and timing are exposed. No anonymity claim follows.

An unspent outpoint identifies this claim's current state; consuming it provides
terminal single-spend behavior on an actual chain. Local populated-transaction
validation alone cannot establish that the outpoint exists or was consumed.
Embedding TN10's domain/genesis distinguishes intended context but cannot by
itself stop execution on another chain that copies identical state and rules.

No security invariant is amended. Independent recovery, private transfers,
multi-user solvency, fees for a continuing pool, reorg handling, and production
setup remain unresolved. See the [A0 evidence report](../poc-a0.md) for measured
results, exact encoding, and reproduction instructions.
