# Adversarial second pass

This is implementation self-review, not independent cryptographic review. All
money/network data is synthetic; no funding is allowed by this package.

- **Inflation:** the actual private circuit constrains authority, membership,
  amounts and integer conservation. Kernel credit requires a unique pending
  native output with matching owner/value; the adapter derives those facts from
  the exact lane transaction's output and committed covenant. Zero/wrong/missing/
  covenant-bound outputs reject. Without native endpoint acceptance, local
  invented transactions are still only fixtures and cannot be counted as deposits.
- **Double spend:** distinct actual old-root proofs produce the same economic
  NF. Current NF state is part of the previous root and survives multiple linked
  batches. Competing/replay guest cases reject without partial ledger updates.
  Deposit credit and recovery share one pending-state consumption record.
- **Wrong prior state:** covenant/config and complete ledger are committed in
  one resource. Swapping the preimage while retaining the previous root fails
  the actual guest assertion. Changing both preimage/root would require changing
  the native predecessor; a bare host-chosen balanced state is not authenticated
  settlement. Production genesis/reorg/canonical predecessor handling is open.
- **Proof forgery:** no caller validity flag or recursive assumption selects an
  outcome. Checked canonical/curve/subgroup/identity decoding precedes the same
  established Groth16 equation. Native Arkworks and accelerated results agree for
  every one of fourteen public-field mutations, all genuine proofs and state
  fixtures. Wrong-subgroup and identity points reject; a canonical subgroup-valid
  false pairing exercises invalid-then-valid inside the guest. The generic host
  verifier trait cannot be selected by serialized input; the guest fixes the
  accelerated implementation and compiled VK.
- **Intent substitution:** actual ciphertext digests, exit destination, domain,
  key identity and all other statement bytes are public inputs. Direct equation
  controls include a changed destination and a changed/rehashed ciphertext.
  Native envelope destination must also match the canonical StandardSpk hash.
- **Omission/reordering:** all actual v1 IDs/payloads, including rejections, feed
  native activity/lane commitments. Removing/reordering/substituting input changes
  the native endpoint. This is a computed mismatch, **not** yet an actually
  rejected native proof for this guest. Higher-layer checks remain required.
- **Unauthorized reserve release:** the guest emits only wallet-authorized exit
  permissions and retains unpaid principal as a liability. It never marks a
  payout confirmed or debits reserve from a host claim. Actual permission use,
  exact destination/value, native single consumption and confirmed lineage must
  be qualified before adding that transition. Native rent/fees remain separate.
- **Privacy/recovery:** guest input contains public state and proof-carrying
  operations only; no keys, openings or selected paths. Bob restored his own local
  synthetic backup in a separate process, recovered his note from public data and
  proved a fresh exit. Parameters are public but large; their checked reload took
  about 49s. Local retention is not independent durable availability. Secrets are
  never copied to B/GPU/Git, and public artifacts are explicitly whitelisted.
- **Liveness/resources:** SDK/runtime/image/key are pinned; development mode is
  disabled for the guest. Authentication tests require their exact assertion;
  resource/IPC failures cannot pass. The full three-proof run hit 128M and stopped.
  No increased budget, fake receipt or omitted input is used to call it success.
- **Remaining trust:** one-party experimental setup, assumed authentic addresses,
  recipient-side encryption validation, four-leaf capacity, zero app fees and
  synthetic anchors remain. No inherited security proof, real anonymity,
  administrator rescue path or production/reorg/migration claim is introduced.

The original local proof artifacts retain their source/identity pins; a compile
feature selects the new target domain explicitly. It does not allow concurrent
cross-domain consumption or silent migration of a user's old note.
