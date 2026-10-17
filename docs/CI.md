# CI scope and local reproduction

CI checks source behavior; it does not qualify a deployment or establish security.
All Actions have read-only repository permissions. No job funds, broadcasts,
starts a node, creates a wallet, runs independent G5, or invokes G6.

| Job | What runs | Evidence boundary |
| --- | --- | --- |
| Documentation checks | Existing Markdown/path checker | Links/structure only; not protocol or external-source correctness |
| Code checks / scope | Freezes the checked commit and detects A0/A1 manifests | A1 absent from a ref is reported explicitly, never counted as tested |
| Code checks / fast | Docs, Python AST + `test_*.py` unittest discovery, all Node syntax + `*.test.mjs`, diff whitespace | Offline unit/SDK serialization tests; no RPC or acceptance observations |
| Code checks / rust (per available component) | Rust 1.91.0 rustfmt and `cargo test --locked --release`, two test threads | Real circuit/unit/native-synthetic tests present in that component; not all retained experiment receipts |

The current main baseline contains A0, A1 and the public native-value/recursive
adapters. Component detection reports exactly what exists in the checked ref.
`workflow_dispatch` may select another ref; all jobs use its resolved commit.
Historical/manual evidence remains separate from unit/CI results.

Native builds use a pinned Rusty Kaspa commit, locked dependencies, Ubuntu 24.04
build prerequisites and caches for Cargo/RocksDB outputs. Node uses version 22
and SDK v2.1.0 with archive SHA256 verification. Installation can access package
registries/GitHub; tests do not depend on live endpoints, balances or fee quotes.
A cold native build is heavier than the fast job and has a 60-minute limit.

From a repository checkout, install Python 3, Node 22, Rust 1.91.0 + rustfmt,
C/C++/Clang/libclang, CMake, pkg-config, OpenSSL headers and protoc. Then:

```bash
bash scripts/ci_setup_sdk.sh
bash scripts/ci_fast.sh
bash scripts/run_poc_a0.sh test
```

The A0 runner obtains/checks the pinned sibling `../upstream/rusty-kaspa` checkout.
Where A1 exists, also run `bash scripts/run_poc_a1.sh test` and rustfmt for each
component. Environment/build failures are not passing tests; record the tested
commit and complete test counts.

Full setup/proving experiments, the 966-case generated A1 corpus, repaired
supplemental cases, SDK/native final-body qualification, stateful receipt/scanner
coupling and container recovery are separate manual evidence runs. They require
the documented pins/artifacts; private backups and large public PK/R1CS bytes
are not CI secrets or repository inputs. See the [reviewer guide](REVIEWER-GUIDE.md)
and PR #22. Retained evidence does not become freshly reproduced because CI is
green. No automated job closes independent-machine/archive G5, live G6,
fixed-fee liveness, setup trust, anonymity or independent human security review.

The PR31 native-value follow-up adds `poc/native-value` to component detection.
Its three Rust tests cover the reused account cycle/rejections, native permission
payout mutations and owner-signature payload binding. Native-value formatting
checks only its two packages, preserving historical vendored code. Fast checks
also exercise lossless JSON/sompi handling and exact reconstruction of corrected
PR31 derivatives from unchanged raw RPC records. These jobs remain offline;
real CPU proving, TN10 settlements and payout evidence are separate runs.

The recursive follow-up adds `poc/takeover` to the Rust matrix. Its package-only
formatting and seven native Rust tests exercise journal/state/context/order,
authorization, replay, image/receipt callback contracts, aggregate continuity
and the reused bridge script cases. Callback tests use explicit test doubles;
CI does not generate recursive proofs or submit transactions. Python syntax
checks include the offline retained-capture harness. Program rebuild, historical
capture preparation and real recursive proof generation are separate local
checks described in the [adapter README](../poc/takeover/README.md).

The shielded-design local package adds a PyNaCl-backed **model** suite to fast
checks and its Python files to syntax checks. CI installs the declared model
requirements before the offline suite. Rust checks build the compatibility host,
not the isolated guest programs or real recursive proofs. Those are manual,
hash-recorded measurements in [the package](../poc/shielded-design/README.md).
Cache fallback is per component/toolchain/native pin; locked dependency resolution
and normal Cargo source checks still apply after restoration. No model/proof test
is native funding, an independent recovery run or proof of financial privacy.
