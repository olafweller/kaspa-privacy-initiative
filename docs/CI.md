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

`main` currently contains A0 and the A1 specification. A1 implementation lives
in draft PR #22. Maintenance CI tests A0; it also tests A1 whenever the selected
ref contains A1. After this workflow is available on the default branch,
`workflow_dispatch` can select `refs/pull/22/head`. It resolves that ref once and
uses the same commit in every job. The selected ref must also include these CI
scripts; bring the maintenance changes onto that branch before dispatching.
Do not claim an A1 run from the maintenance PR's A0-only matrix.

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
