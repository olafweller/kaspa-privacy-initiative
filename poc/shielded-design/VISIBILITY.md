# Visibility and retained-data contract

Proposed interface under [RFC-0002](../../docs/rfc/0002-shielded-payment.md).
The model is not a privacy proof. A public ledger observer also sees native
funding, fees, transaction size/order and network-observable correlations.

| Data | Wallet / recipient | Executor and outer prover | Kaspa / public archive | Requirement / current status |
| --- | --- | --- | --- | --- |
| Input note value, randomness, spending/nullifying keys | Spending wallet only; receiver learns its own delivered note | Must not receive | Must not receive | Required in full wallet proof; model oracle knows synthetic test witnesses, not a deployable verifier. |
| Selected input leaf/index/membership path | Rebuilt locally | Must not receive | Must not receive | Historical root public; selected witness remains private. No per-owner public resource ID. |
| Input-to-output linkage | Sender and recipient know their own context | Should not learn from private data | Hidden cryptographically, subject to traffic/amount inference | No anonymity claim from a one-depositor/one-payment demonstration. |
| Membership anchors, current nullifiers, note commitments | Public inputs | Public state | Retained authenticated data | Nullifiers must not reveal which old commitment was spent. Model HMAC identifiers are not a selected construction. |
| Wallet public intent and proof | Created locally | Required for actual verification/composition | Full proof availability or authenticated alternative needed | Intent excludes proof bytes to avoid circular native-ID dependency. Final wire format not implemented. |
| Output ciphertext and ephemeral encryption data | Recipient decrypts locally | Opaque public data | Full accepted records retained | Fixed-width model plaintext and standard sealed boxes; no final cipher/address protocol selected. |
| Owner/recipient receiving-address keys | Exchanged privately/out of band as appropriate | Do not publish per-user accounts | Must not appear as private-note owner IDs in lane payload | Model signs the receiving-address binding to detect key substitution. |
| Native deposit amount/output and eventual native payout | Public | Public | Public | Entry/exit remain transparent, enabling timing/amount correlations. |
| Exit destination/principal and unpaid permission rent | Public once exit requested | Must enforce exact fields | Native payout and permission output observable | No debit-as-payment claim; refunds remain backed liabilities. |
| Private fee claim terms | Authorized in wallet intent | Public claim sufficient for first model | Fee funding/claim payout visible | A user's public funding wallet must not be silently presented as anonymous; independent fee availability is unresolved. |
| Logs/journals | Synthetic diagnostics only | Public fields only | No secrets in proof journal | Measured fixture journal is a retained native ID plus two hashes; fixtures/secrets are explicitly public test data. |
| Old verifier/format and migration data | Required for legacy spend | Version-bound public verification | Retained exact artifacts/lineage | Unsupported versions rejected now; no migration availability guarantee. |

## Bob's independent receive/spend within the model

Bob receives only his own wallet keys plus public accepted output/commitment
records. He trial-decrypts locally, rejects corrupt or mismatched commitments,
validates the spending-owner binding and obtains a membership snapshot from
public protocol data. He can request a model spend/exit without Alice's wallet
or an executor's private note database. Viewing material alone cannot authorize
spending. This is logical role separation in one local test harness, not an
independent-machine shutdown test.

## Data required after services disappear

Retain enough accepted-history/snapshot evidence to authenticate commitments,
nullifiers, paid/unpaid exits, deposit consumption and allowed roots, plus full
ciphertexts, delivery metadata and pinned software/verifiers. Users retain their
own secrets and required note backups. Losing ciphertexts can prevent discovery;
losing commitment history can prevent witness rebuilding. A valid root does not
repair either. The later N-user shutdown/exit gate remains required.

## What the model can and cannot establish

Assertions check public payloads do not contain selected input commitment,
owner key, note randomness or path/index; they exercise fixed-size ciphertext
encoding and reject a substituted receiving encryption key. These checks catch
specified implementation mistakes. They do not prove zero knowledge, PRF
unlinkability, constant-time wallet behavior, private network access or anonymity.
Metadata, traffic, proof/operation arity, public fees and low activity remain.
