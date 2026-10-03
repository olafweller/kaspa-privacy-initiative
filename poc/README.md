# Proof-of-Concept Plan

The first PoCs are designed to answer narrow technical questions, not to simulate a finished product.

Use **test KAS only**.

## A0 — reserve-release feasibility sub-spike

The [A0 experiment](../docs/poc-a0.md) tests a real Groth16 authorization proof
and exact payout constraints through pinned Kaspa consensus code. Its supplied
local UTXO is not a funded TN10 reserve. A0 is narrower than PoC A below and does
not satisfy the private-transfer or independent-recovery milestones. See
[ADR-0002](../docs/adr/0002-a0-reserve-release-experiment.md) for the bounded scope;
ADR-0001 remains Proposed.

## PoC A — Fund safety + private transition

### Question

Can native test KAS become backing for a private claim, change ownership privately, and later be withdrawn by the rightful owner without exposing the internal transfer amount on the public ledger?

### Target flow

```text
Alice shields 100 test KAS
        |
        v
private note / claim exists
        |
Alice privately transfers 37 to Bob
        |
        v
old private input consumed
new private outputs created
        |
        v
Bob can later prove an authorized claim
        |
        v
native test KAS can be unshielded
```

The exact public withdrawal amount/timing used in the privacy analysis should not be chosen in a way that falsely makes the demo look more anonymous than it is.

### Required demonstrations

1. Real test KAS backs the private state.
2. The internal transfer value is not directly exposed as a normal public 37 KAS payment.
3. Value is conserved.
4. Only the rightful spender can consume a private claim.
5. The same input cannot be spent twice.
6. Wrong/stale state proofs fail.
7. Malformed proofs fail.
8. Unauthorized withdrawal fails.
9. The reserve cannot be drained beyond valid claims.

### Required adversarial tests

- modify the claimed output value;
- reuse a nullifier;
- replay a proof;
- submit a proof against the wrong state root;
- attempt a negative/overflow/range edge case;
- withdraw without valid ownership;
- use a stale witness;
- alter a public binding used by the proof.

## PoC B — Failure / replaceability

### Question

Does the architecture remain safe and recoverable if the normal infrastructure disappears?

### Experiment

1. Build a valid private state with several users.
2. Stop the default prover/executor/state service.
3. Start a clean independent environment.
4. Reconstruct the required public state.
5. Restore one user's private wallet material.
6. Continue proving or perform a valid exit.

### Success criteria

- no special founder/operator key is needed;
- no user reserve funds are lost;
- a replacement prover can be used;
- state can be independently verified;
- failure may delay progress but does not enable theft.

## PoC C — Privacy leakage analysis

After PoC A works, measure what an observer can still infer from:

- shielding amount/time;
- unshielding amount/time;
- public fees;
- transaction submission;
- RPC/note discovery;
- note-selection behavior.

The purpose is to distinguish:

```text
cryptographic confidentiality
```

from:

```text
real-world unlinkability
```

## Explicitly not required yet

Do not build in the first PoC:

- a mobile wallet;
- a DEX;
- NFT support;
- swaps;
- a governance token;
- a DAO;
- production fee economics;
- a marketing site;
- mainnet deployment;
- custom cryptography merely to appear innovative.
