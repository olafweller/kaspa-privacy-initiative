# Threat Model

**Status:** initial research draft. This document should become more precise as architecture choices are made.

## Assets to protect

1. Native KAS backing the shielded system.
2. The integrity of the shielded supply.
3. User authorization and spend rights.
4. Sender privacy.
5. Recipient privacy.
6. Amount privacy.
7. Balance privacy.
8. Transaction-graph unlinkability.
9. Availability of valid exits.
10. The ability to reconstruct and independently verify protocol state.

## Primary security goals

An attacker must not be able to:

- create unbacked shielded KAS;
- spend the same private value twice;
- withdraw another user's funds;
- alter a valid state transition without detection;
- make an invalid proof accepted;
- make a valid user's funds dependent on one trusted operator;
- silently change the protocol rules through a privileged key.

## Adversaries

The system should consider:

- malicious users;
- blockchain analytics companies;
- large passive observers;
- malicious or compromised provers;
- malicious executors/sequencers;
- compromised RPC/state servers;
- compromised wallet software;
- colluding infrastructure operators;
- attackers seeking denial of service;
- attackers exploiting implementation bugs;
- governance or treasury capture;
- adversaries with exchange/KYC information;
- long-term observers correlating deposits and withdrawals.

## Attack classes

### 1. Inflation

A bug in the circuit, arithmetic, commitment scheme, proof verifier, or state transition allows more shielded value to exist than native KAS locked by the protocol.

**Severity:** catastrophic.

### 2. Double spending

The same note/value can be consumed more than once because nullifiers are not unique, not correctly bound, or not consistently checked.

**Severity:** catastrophic.

### 3. Unauthorized withdrawal

An attacker convinces the settlement mechanism to release native KAS without owning a valid shielded claim.

**Severity:** catastrophic.

### 4. Malicious prover

A prover submits a forged, stale, incomplete, or wrongly-bound transition proof.

Desired property: an invalid proof cannot threaten safety. Loss of a prover may threaten liveness only.

A hosted prover may also learn private notes, amounts, and other witnesses supplied to it. A zero-knowledge proof does not hide those inputs from the prover that handles them. Record local/outsourced proving assumptions and keep spend secrets out of untrusted execution infrastructure.

### 5. Malicious executor/sequencer

An executor censors, reorders, withholds, or selectively includes operations.

Questions:

- Can another executor take over?
- Can censorship be detected?
- Can users still exit safely?

### 6. State availability failure

A server or group disappears with data needed to generate future proofs or withdrawals.

Desired property: critical state is public/reconstructable, replicated, or user-held such that disappearance of common infrastructure does not destroy funds.

Roots alone cannot reconstruct state or witnesses. Recovery must account for L1 pruning, retained public history, encrypted note delivery, wallet backups, and independent proving. A safe halt is not evidence of recoverability.

### 7. Witness corruption

Wallets or provers receive incorrect Merkle paths, state roots, note metadata, or encrypted payloads.

The system should verify rather than trust witness providers wherever practical.

### 8. Timing correlation

A user shields a distinctive amount and soon unshields a similar amount. Even perfect ZK may not prevent a strong statistical link.

### 9. Amount correlation

Unique public deposit/withdrawal values may reduce the practical anonymity set.

### 10. Network metadata

RPC requests, note scanning, transaction submission, IP addresses, and peer connections may reveal relationships that the ledger itself hides.

### 11. Wallet fingerprinting

Wallet-specific transaction construction, timing, fee behavior, note selection, or relay patterns may identify a user or software version.

### 12. Viewing-key leakage

A compromised viewing key may reveal incoming activity or other metadata depending on the final key model.

### 13. Cryptographic failure

A primitive, curve, proof system, hash, PRF, or implementation assumption becomes insecure.

Cryptographic agility must be balanced against upgrade risk.

### 14. Circuit/spec mismatch

The implementation proves a subtly different rule set than the written specification.

Independent test vectors and cross-implementation testing should reduce this risk.

### 15. Upgrade capture

A governance process, multisig, or maintainer group gains the ability to replace the settlement logic with rules that can confiscate or redirect funds.

### 16. Treasury capture

A development funding mechanism becomes technically or socially entangled with user reserves.

The two must remain separate.

### 17. Denial of service

Attackers spam commitments, nullifiers, proofs, or state requests to make proving or verification too expensive.

### 18. Reorg / finality assumptions

An application acts on a Kaspa state transition before the required finality assumptions are satisfied, leading to inconsistent state or invalid settlement.

Define rollback/replay behavior and distinguish executed, proved, settled, and withdrawable state. Historical note anchors must not authorize replay against stale settlement or spent-state roots.

### 19. Unpaid exit liability

A private claim is consumed into an exit entitlement, but the reserve accounting drops that entitlement before the user receives an authorized payout. All pending exits remain user liabilities; proofs and settlement must bind the amount, destination, reserve continuation, and any fees.

## Initial out of scope for the first cryptographic PoC

The first PoC may not fully solve:

- IP/network privacy;
- mobile light-client privacy;
- economic spam resistance;
- production-grade prover decentralization;
- polished recovery flows;
- legal/operational deployment.

These are not out of scope for the eventual protocol. They are only deferred so the first experiment remains falsifiable and small.

## Principle

**A privacy protocol is not secure merely because transaction contents are encrypted or hidden in a proof.**

The entire path — deposits, state availability, proving, note discovery, transaction broadcast, exits, wallet behavior, and upgrades — belongs in the threat model.
