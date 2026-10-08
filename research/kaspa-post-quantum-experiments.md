# Kaspa-native post-quantum experiments

Research note for [issue #19](https://github.com/olafweller/kaspa-privacy-initiative/issues/19)
(post-quantum requirements and migration). This note surveys three public
experiments that verify post-quantum (PQ) signatures on Kaspa testnet-10 (TN10)
or prepare to. It selects no proof system or signature scheme and changes no
architecture decision, invariant or experiment.

Reviewed 2026-10-08. Sections separate **facts** (observed in source or on
chain), **interpretation** (our reading) and **hypotheses** (untested).

## Sources and pins

| Repository | Pinned commit | Licence | Commits |
| --- | --- | --- | --- |
| [KaspaKii/kaspa-pq-zk-bench](https://github.com/KaspaKii/kaspa-pq-zk-bench/tree/388de9cc8cdcf4db419dec871913bdc21635f882) | `388de9cc8cdcf4db419dec871913bdc21635f882` (2026-07-22) | MIT | 2 |
| [aglov413/kaspa-pqv](https://github.com/aglov413/kaspa-pqv/tree/960d6ed24b8babe08f67d547ad3d3a2ab4121fe8) | `960d6ed24b8babe08f67d547ad3d3a2ab4121fe8` (2026-09-21) | Apache-2.0 OR MIT | 12 |
| [biryukovmaxim/kaspa-xmss](https://github.com/biryukovmaxim/kaspa-xmss/tree/e36538f98c08ae7def78de5e66065c96169b69b6) | `e36538f98c08ae7def78de5e66065c96169b69b6` (2026-07-03) | none stated | 69 |

KPI did **not** build, test or run any of them. Every cost and benchmark below
is reported by the authors unless marked otherwise.

## 1. kaspa-pq-zk-bench — PQ signature verification inside a RISC Zero STARK

**Facts (source).**

- Verifies ML-DSA-44 (FIPS 204), SLH-DSA-SHA2-128s (FIPS 205) and
  FN-DSA/Falcon-512 (FIPS 206 draft) inside RISC Zero zkVM guests. Signing and
  key generation happen on the host. The guest commits `(public key, message,
  true)` to the journal ([guest](https://github.com/KaspaKii/kaspa-pq-zk-bench/blob/388de9cc8cdcf4db419dec871913bdc21635f882/methods/guest/src/main.rs)).
- Output is a RISC Zero *succinct* receipt for Kaspa's KIP-16 `OpZkPrecompile`
  (`0xa6`) tag `0x21`, the tag KPI already documents in
  [kaspa-toccata-vprogs.md](kaspa-toccata-vprogs.md).
- The helper `build_pq_anchor_redeem` places **all proof fields, including
  seal and journal, inside the redeem script** and ends with `OpZkPrecompile`
  ([host/src/lib.rs](https://github.com/KaspaKii/kaspa-pq-zk-bench/blob/388de9cc8cdcf4db419dec871913bdc21635f882/host/src/lib.rs)).
  The script does not introspect the spending transaction.
- Proving times on an RTX 4090 are attributed to a third party (GhostProver /
  NTH MOMENT): Falcon-512 1.91 s, ML-DSA-44 5.35 s, SLH-DSA-128s 16.33 s, mean
  of five runs. They used RISC Zero 3.0.6 while the repository pins 3.0.5. Raw
  logs and proof artifacts are committed
  ([benchmarks/rtx4090](https://github.com/KaspaKii/kaspa-pq-zk-bench/tree/388de9cc8cdcf4db419dec871913bdc21635f882/benchmarks/rtx4090)).
- **No TN10 transaction id is published.** SETUP.md describes an optional
  TN10 lock/spend procedure only.

**Interpretation.**

- This is a proving benchmark plus a route to on-chain STARK verification. It
  is **not** PQ ownership of funds: the redeem script authorizes no specific
  spend, so once the script is revealed any spender can choose the outputs.
  Binding a PQ signature to a spend would need the signed message to be
  constrained to the transaction (e.g. via introspection or a journal check
  against transaction fields). This repository does not demonstrate that.
- It shows that lattice schemes needing SHAKE are realistic only through a
  zkVM. Kaspa script lacks Keccak/SHAKE, as kaspa-pqv also notes.

## 2. kaspa-pqv — hash-based signatures verified directly in Kaspa script

**Facts (source).**

- P2SH "vault" addresses whose redeem script verifies SLH-DSA (FIPS 205 `128s`;
  SP 800-230 draft `128-24`; non-standard `128-24d2`) or stateful LMS
  (RFC 8554, `h=15`, `w=2`) **directly in Kaspa script**. No ZK proof or new
  opcode. Uses KIP-10/KIP-17 introspection and v1 `compute_budget`
  ([README](https://github.com/aglov413/kaspa-pqv/blob/960d6ed24b8babe08f67d547ad3d3a2ab4121fe8/README.md),
  [spec](https://github.com/aglov413/kaspa-pqv/blob/960d6ed24b8babe08f67d547ad3d3a2ab4121fe8/docs/vault-spec.md)).
- The signature commits to a **binding digest reconstructed in script from
  transaction introspection**: version, outpoint, output count and every output
  amount/script. A fixed two-output shape (destination plus change) and one
  vault input per spend are assumed.
- Authors' measured costs (one input, two outputs; testnet mass parameters):

  | Scheme | Stateful | Redeem B | Tx bytes | Script units | Fee (tKAS) |
  | --- | --- | --: | --: | --: | --: |
  | LMS h=15 w=2 | yes | 19,717 | 24,891 | 375,226 | 0.0498 |
  | SLH-DSA-128s | no | 89,235 | 97,473 | 1,285,456 | 0.1949 |
  | SLH-DSA-128-24 | no | 21,752 | 25,926 | 266,270 | 0.0519 |
  | SLH-DSA-128-24d2 (non-standard) | no | 33,664 | 40,194 | 455,267 | 0.0804 |

- Ten TN10 txids are listed as confirmed spends (August–September 2026). On
  2026-10-08 **none was found** by the public TN10 index `api-tn10.kaspa.org`
  ("Transaction not found"), while KPI transactions from 2026-10-03 were
  found. The cause (index retention, reset or otherwise) is unknown.
- Self-declared: not audited, never run on mainnet. Builds against a local
  `rusty-kaspa` checkout by path, not a pinned git revision.
  `128-24` is a draft parameter set; `128-24d2` is not standardised.
- LMS needs a durable sign-once journal. Signatures produced off chain can
  expose a one-time key, as the README states after core-developer review.

**Interpretation.**

- This is the most directly relevant result for PQ ownership on current L1:
  stateless SLH-DSA authorization bound to the spend, using only Toccata
  primitives. Our A1 reserve and exits currently use Groth16 plus classical
  secp256k1 payout keys.
- Costs are dominated by script and witness bytes (transient mass). For KPI,
  the cost of a PQ ownership check per exit or per note spend would add to the
  cost of the ZK verification.

## 3. kaspa-xmss — stateful XMSS^MT with an on-chain reuse-proof covenant

**Facts (source).**

- XMSS^MT per NIST SP 800-208 / RFC 8391 profile: 2^24 signatures, two
  height-12 trees, 24-byte hashes (BLAKE3/192 default), ≈3.06 KB signatures
  ([spec](https://github.com/biryukovmaxim/kaspa-xmss/blob/e36538f98c08ae7def78de5e66065c96169b69b6/docs/xmssmt-scheme-spec.md)).
- Verification compiles to Kaspa script. The message is **derived live from
  transaction introspection**
  ([covenant.rs](https://github.com/biryukovmaxim/kaspa-xmss/blob/e36538f98c08ae7def78de5e66065c96169b69b6/crates/xmss-script/src/covenant.rs)).
- One-time-key reuse is prevented on chain by a two-script covenant: a
  KIP-20 covenant-id singleton carries a monotonic counter `i -> i+1` in its
  successor address, with a bounded skip window for fee bumps and crash gaps
  ([two-script-covenant.md](https://github.com/biryukovmaxim/kaspa-xmss/blob/e36538f98c08ae7def78de5e66065c96169b69b6/docs/two-script-covenant.md),
  [covenant-recovery-and-skips.md](https://github.com/biryukovmaxim/kaspa-xmss/blob/e36538f98c08ae7def78de5e66065c96169b69b6/docs/covenant-recovery-and-skips.md)).
- [tn10-example.md](https://github.com/biryukovmaxim/kaspa-xmss/blob/e36538f98c08ae7def78de5e66065c96169b69b6/docs/tn10-example.md)
  describes an observed TN10 bootstrap and lineage step but publishes **no
  txids**. Dependencies follow `rusty-kaspa` `branch = master` (lockfile
  revision `a8951cd4`). Explicitly experimental and unaudited.

**Interpretation.**

- The covenant lineage pattern (counter in successor script, singleton id,
  one live UTXO per id) resembles KPI's A1 S0 → S1 successor state. It is a
  concrete example of covenant-enforced state replacing wallet-only state.
- Stateful keys still need non-exportable counters and burn-on-restore
  backups. This affects recovery designs such as A1's independent B machine:
  a restored backup must never roll a counter back.

## Comparison

| | pq-zk-bench | kaspa-pqv | kaspa-xmss |
| --- | --- | --- | --- |
| Primitive | ML-DSA, SLH-DSA, Falcon | SLH-DSA, LMS | XMSS^MT |
| Where verified | RISC Zero succinct STARK via KIP-16 tag `0x21` | Kaspa script | Kaspa script |
| Bound to spending tx | No (proof baked into redeem script) | Yes (introspected digest) | Yes (live message) |
| Stateful keys | No | LMS yes, SLH-DSA no | Yes (covenant counter) |
| Kaspa features | KIP-16 | KIP-10, KIP-17, v1 compute budget | KIP-10/17/20 covenants |
| TN10 evidence | None published | 10 txids, not found in public index 2026-10-08 | Described, no txids |
| Reproduced by KPI | No | No | No |
| Audit | None | None | None |

## Relevance to KPI

**PQ ownership of notes (hypothesis).** A future shielded design proves note
ownership inside the ZK proof. A PQ spending key would then be verified in the
circuit, not in script. kaspa-pqv shows the script-level cost of a direct
check; zkVM benchmarks show the in-proof cost. Neither shows note privacy.

**Reserve and exits (interpretation).** A1's terminal payout goes to a
classical secp256k1 P2PK recipient. A PQ exit could pay to an SLH-DSA vault
address of kaspa-pqv style without changing the covenant. Reserve release
itself is gated by the proof system, not by a signature.

**Proof system security (fact plus interpretation).** Groth16/BN254, used by
A0/A1 (tag `0x20`), relies on pairings over elliptic curves and is broken by a
large quantum computer. RISC Zero succinct receipts (tag `0x21`) are
hash-based STARKs and are generally considered plausibly post-quantum, subject
to their stated soundness level and hash assumptions. A PQ signature verified
inside a Groth16 circuit gives no PQ security, because the final proof can be
forged. A PQ signature inside a STARK is not enough either if payout keys,
note encryption, commitments or setup elsewhere stay classical.

**Crypto-agility (open).** All three experiments bake parameters into the
address or script. Changing the scheme means a new address and moving funds.
For KPI this means the following have to survive migration:
- user funds, independent exits and recovery;
- value conservation (I-2) and replay protection;
- no privileged withdrawal authority (I-8, I-13);
- protection against downgrades.

A versioned verifier identity, with user-initiated migration through a proof
of the old note under the old rules, is a candidate pattern. It is unevaluated
and needs an ADR.

**Architecture compatibility (no selection).** Direct script verification
fits candidate A's covenant and B's shards equally, at a byte cost per input.
Candidate C (based app / vProgs) would more naturally verify signatures inside
the guest program and settle with one proof, which makes the proof system's PQ
status decisive.

## Unresolved questions

1. Can a PQ signature be bound to a spend through a tag-`0x21` journal check
   against introspected transaction fields, and at what mass?
2. What soundness level do RISC Zero succinct receipts provide under Kaspa's
   verifier, and which hash functions does it assume?
3. Can SLH-DSA verification for a shielded spend live in a STARK guest at an
   acceptable proving time on non-GPU hardware (the authors report minutes on
   CPU)?
4. How would A1-style independent recovery handle stateful PQ keys (counters,
   backups) without reuse?
5. What migration path moves existing Groth16-gated reserves to a PQ verifier
   without an admin key or a downgrade window?

## Risks and limitations of this note

- Benchmarks and TN10 claims are not independently reproduced. The kaspa-pqv
  txids could not be found in the public index on the review date.
- Two parameter sets in kaspa-pqv are draft or non-standard.
- No repository is audited. Unrolled verifier scripts of 20–90 KB fail in both
  directions: too permissive means theft, too strict means stuck funds.
- Statements on STARK post-quantum security are general literature
  positions, not a KPI analysis.

Next step for issue #19: decide which question above to test first,
preferably (1) or (3), as an isolated unfunded experiment with its own ADR
entry before any implementation.
