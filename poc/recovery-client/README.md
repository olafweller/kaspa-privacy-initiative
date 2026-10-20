# User-owned Linux wallet start kit

This is the first user-computer preparation step for the fresh TN10 recovery
trial. PR58 is merged at `52bb2b4e7a1e0a8f98aecb58d33933f0b03d9e33`.
Its six-receipt proof evidence and the old PR54 instance remain unchanged.
No server service is stopped, GPU rented, setup generated, or transaction funded
or broadcast by this kit.

The owner selected a Linux Mint computer with a local Codex installation. Give
that local session the task to prepare the existing reviewed wallet on **that
computer**; the Cloud agent cannot execute commands on the user's PC through
its TN10/B administration route. There is no new remote terminal or key transfer.

## What is delivered

[KPI-wallet-start-linux-x86_64.zip](KPI-wallet-start-linux-x86_64.zip) is a
1.5 MB download containing the existing PR56 wallet binary, a small offline
launcher, Dutch start instructions and the seven public recovery fixture files.
Its exact identity is in [package-identity](evidence/package-identity.json).
The binary SHA256 remains
`aeb84c7a3edd9b076e28c3035729fca9df0d582e44d33cbc951d697fb33c3c90`;
its reviewed source is not modified or rebuilt. Linux x86_64 with glibc >=2.34
and Python 3 is required. Mint 21/22 x86_64 are suitable target families; actual
Mint execution is still for the user's local Codex to confirm. Cloud qualification
ran on Linux, not that physical computer.

- `python3 client.py doctor`: validates the package, runs the actual wallet with
  a temporary test wallet, reconstructs all six retained public fixture inputs
  and checks scanning/wrong-root rejection. No real user wallet is created.
- `python3 client.py init ~/kpi-testwallets`: creates fresh Alice/Bob wallets,
  private directories/files and separate public-only address files. Existing
  directories are never overwritten; partial creation is retained on failure.
- `python3 client.py public ~/kpi-testwallets`: reads only the two public receive
  files with the exact four-field allowlist. It does not inspect backup contents.

Both users are logical roles administered by the same owner. This establishes
user-computer secret placement and preparation, not independent administration
by two humans or protection against the PC administrator. Backups are not
encrypted. Keep secret working files in the native Linux home, not a synced or
Windows-mounted folder, and back them up only to owner-controlled media.
The kit requires no provider/account/API key and makes no network requests.
Wallet children receive a small explicit environment without remote credentials.

## Local Codex handoff

The owner can paste a task into their Mint Codex session. It should:

1. Check it is running on the user's Mint workstation, as the normal user,
   not on Cloud, B or TN10. Check architecture, libc and Python.
2. Download the public ZIP over HTTPS at the exact reviewed source commit.
   Compare its SHA256 with the separately supplied package identity **before
   extraction or execution**. Use a fresh directory in the user's home.
3. Run `doctor`, then initialize fresh test wallets only if it succeeds. If an
   earlier user wallet exists, preserve it and report the situation; do not
   silently create another funded identity or overwrite keys.
4. Tell the owner where the four secret backup files live without printing or
   sending their contents. Ask locally for a backup destination if a copy is
   needed. Only the two files under `public/` are shareable with Cloud.
5. Return a short readiness result (architecture, libc, doctor result, wallet
   directory and public filenames); no secret logs, SSH credentials or uploads.

The downloaded source and its given hash are the trust anchor. The internal
manifest detects damage but does not authenticate itself against a malicious
replacement of the entire distribution.

## Qualification and remaining work

```bash
python3 poc/recovery-client/test_client.py
```

The actual packaged binary passes offline restore, fresh two-role initialization,
permissions, public-field allowlisting and rejection of overwrites, mounted
working directories, extra receive fields, symlinks, binary tampering and fixture
tampering. The test also rebuilds the ZIP byte-for-byte from the source and pinned
binary. [Qualification](evidence/qualification.json) and the separate CPU-only
CI job preserve these checks without changing historical workflow bindings.

This is **onboarding, not a start-ready six-stage live trial**. Integrating actual
chain data with the new recovery guest, a staged six-proof producer/service,
Alice's local credit/transfer generation, independent accepted checkpoints,
public parameter delivery and both genuine live payouts remain required. The
original wallet binary already contains rebuild/scan/exit commands, but no exit
is executed by this launcher. Later proofs require the same retained public
parameters, SHA256
`812b3bda0ec5f9b0c17fc1d530e49fc21defc9dcc5ea9c70a133ca62fec31e99`;
those 156,439,536 public bytes are not needed or bundled for onboarding.
Do not substitute the smaller earlier Groth16 comparison parameter file or
create a new setup. No GPU time is running while the user prepares this computer.

## Adversarial second pass

The kit adds no signing/broadcast route, changes no monetary relation and cannot
release reserve funds. It copies only allowlisted public address fields; backups
and native keys are generated by the unchanged trusted wallet on the user's PC.
It never bundles pre-created user keys. Fresh-directory creation prevents silent
overwrite; partial setup preserves any generated keys instead of deleting them.
Verified binaries are made executable only after integrity checks. Fixture replay
is labelled offline and cannot establish a current accepted checkpoint. Losing
the PC or public history remains a recovery dependency; no reset/admin path is
introduced. Same-owner Alice/Bob roles and plaintext local backups remain explicit.
