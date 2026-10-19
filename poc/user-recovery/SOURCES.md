# Reuse review — 2026-10-19

Rechecked all ten upstream heads in [source-refresh](evidence/source-refresh.json).
The pinned Kaspa/vProgs, Orchard, Aztec, RAILGUN and MWEB heads are unchanged.
Monero advanced; this work retains its previously inspected range/conservation/
authorization separation, and does not import new Monero code.

Revisited the primary sources retained in the [wallet review](../private-note-wallet/SOURCES.md)
and [native mapping](../private-native/SOURCES.md): Orchard note encryption and
nullifier source, Aztec note interface, RAILGUN transaction-note decoding, Monero
rctSigs, MWEB OutputMessage scan data, Kaspa Toccata based-apps and research text.
Reuse recipient trial decryption plus commitment reconstruction, current
nullifier checks, and independently authenticated public state; do not claim a
backup/root alone supplies missing history. No circuit/encryption/curve source
from those projects is copied.

Inspected pinned vProgs `permission_script.rs` at f9b84a8: terminal permission
consumption refunds rent, and `emit_verify_delegate_balance` deliberately omits
delegate change when the exact reserve is consumed. Reuse that branch unchanged,
with a restrictive native prefix and actual pinned TxScriptEngine tests. The
PR49 positive-change script and PR54 guest remain unmodified. See
[ADR-0016](../../docs/adr/0016-user-held-recovery-and-terminal-exit.md).
