# Initial Repository and Publication Review

**Date:** 2026-10-02

**Status:** initial findings and publication follow-up; no architecture accepted and no production cryptography started.

## Publication follow-up

On October 2, 2026, the project steward approved the proposed editorial and structural corrections and authorized public GitHub publication. The original baseline and findings below are retained as a historical record; they describe the workspace before publication setup.

- Clarified temporary development controls without allowing reserve/proof bypasses.
- Added deposit, pending-exit, fee, and payout specification requirements; kept the security invariants unchanged.
- Clarified note inclusion versus authenticated spent-state checks, asynchronous execution versus settlement, recovery data/pruning/reorg requirements, and prover confidentiality in architecture, open questions, and the threat model.
- Revised unsubstantiated safety/throughput language while keeping all three architecture candidates open.
- Added the canonical Apache-2.0 license, contributor walkthrough, proposal IDs, issue templates, and a minimal documentation check/CI workflow.
- Published the [repository](https://github.com/olafweller/kaspa-privacy-initiative) with Issues and Discussions. Private vulnerability reporting is enabled. The initial documentation workflow passed.

ADR-0001 remains Proposed. Approval of these corrections is not acceptance of a state architecture or authorization to start production cryptography. The live issue tracker carries ongoing research and review. All fifteen backlog proposals have public issues; a documentation starter task and a welcome discussion provide entry points for new contributors.

## Scope and baseline

Read all 34 initial files, including the core documents, research notes, ADR template, PoC plan, GitHub issue/PR templates, and `.gitignore`. The tree is documentation-only and matches `FILE-INDEX.md` at the directory level. There is no code, package/build configuration, CI workflow, or canonical `LICENSE` file.

`git status --short --branch` fails because this workspace has no `.git` metadata. There is no branch, commit, remote, or clean/dirty status to report. A temporary file-content baseline was captured outside the repository to verify edits; no Git repository was initialized. There is no configured GitHub destination here, so the proposed issues remain a backlog; no external issues were created.

No node, wallet, prover, or TN10 transaction was run. This is a documentation/source review, not a security audit or validation of network behavior.

## Changes made within this review

- Removed the requested third-party discussion, claim, URL, and named research tasks throughout the repository; retained a general existing-work requirement.
- Drafted [ADR-0001](adr/0001-state-architecture.md) comparing A/B/C, with all I-1 through I-16 retained as requirements. Status is Proposed; investigation order is a recommendation only.
- Updated [the upstream notes](../research/kaspa-toccata-vprogs.md) with exact default-branch commits, implemented verifier interfaces, current release, prototype limitations, and untested gates.
- Reworked [the existing-work note](../research/existing-kaspa-privacy.md) to separate a prior forum question, inspected code, historical security issue, and architecture hypotheses. Removed unattributed developer-feedback assertions.
- Removed one dead RAILGUN source URL. Added review/ADR navigation to the architecture document, ADR index, and file index.

No candidate architecture was selected. The threat model, principles, PoC plan, and security invariants were not rewritten.

## Link results

All 22 initial relative Markdown links resolved to existing paths. No initial link contained a local heading fragment. Code-formatted file references in the index/bootstrap documents also refer to existing files, apart from the explicitly future ADR filename that is now supplied.

Checked the 21 distinct initial external URLs remaining after the requested removal. One confirmed HTTP 404 was `research/railgun.md`'s community FAQ privacy-basics URL; removed it because the adjacent privacy-system source is valid. Four GitHub blob requests returned HTTP 503, not confirmed missing files: both Toccata guide files and both Litecoin documents. The Toccata files were retrieved successfully at a pinned docs commit; both Litecoin raw files returned HTTP 200. The other 16 URLs returned HTTP 200. HTTP availability does not establish source correctness or freshness.

New source links use reviewed commit/file paths where possible. Upstream references themselves have drift: `vprogs/docs/proving-pipeline.md` and the old Rusty Kaspa `examples/zk-covenant-rollup` path are absent at the reviewed heads. Do not transplant those paths into a PoC.

Final local verification: all 44 relative Markdown links resolve; all 28 distinct pinned upstream links match the inspected commit trees; the requested removed name has zero matches in repository files. No files were deleted. Ten existing files changed and two documents were added.

## Upstream findings

| Finding | Evidence | Implication |
| --- | --- | --- |
| Toccata is reported live since June 30, 2026; current node source is post-Toccata | [Builder overview](https://kaspa.org/build), [v2.1.0 release](https://github.com/kaspanet/rusty-kaspa/releases/tag/v2.1.0), active KIPs in the [source map](../research/kaspa-toccata-vprogs.md) | Keep the live-capability statement, while distinguishing it from pool feasibility. |
| Latest release is v2.1.0, September 22; builder banner still says v2.0.1 | Release/API metadata and builder page | Pin source/release data rather than relying on the landing-page banner. |
| `OpZkPrecompile` supports BN254 Groth16 and RISC Zero Succinct, with explicit stack encodings and metering | Pinned verifier/tag source in the source map | ZK support does not mean every proof system or layout is supported. Measure complete transaction budgets. |
| vProgs supplies runtime, settlement, withdrawal, and catch-up components but remains a prototype | Pinned README, guest, withdrawal, settlement source, and runbook | Components are research references; no stable external API or audited private-state implementation is established. |
| TN10 demo defaults to development mode and a dev redeem | Pinned TN10 runbook and settlement builder | Useful for plumbing; cannot demonstrate I-5 proof soundness. |
| Issue #77 is closed; reviewed code contains payout-amount checks | [Issue #77](https://github.com/kaspanet/vprogs/issues/77), pinned permission script | Retain the lesson about full payout binding; do not claim an unresolved bug. |
| Full-vProgs specification remains v0.0.1 draft | Pinned `kaspanet/research/vProgs/main.tex` | Separate future composition/L1 requirements from a single based app using current sequencing. |
| Prior optional-privacy post is a question, not a completed design | [September 8 forum post](https://research.kas.pa/t/optional-privacy-layer-for-kaspa-similar-to-litecoin-mweb/522) | Acknowledge prior discussion without treating it as implementation evidence. |

No complete shielded pool was verified in the reviewed official files. This limited inspection cannot exclude other repositories or branches. The mature-protocol notes provide useful starting points but do not yet satisfy a component-level reuse/adapt/reject review.

## Corrections proposed before publication

These were proposed in the initial review. The publication follow-up above records the approved clarifications; the invariants remain unchanged and unresolved protocol details remain research tasks.

1. **Temporary controls need tighter wording.** `PRINCIPLES.md` section 5 permits temporary testnet controls, while AGENTS and I-7/I-8 prohibit convenience withdrawal authority and privileged fund control. Clarify that development controls cannot bypass reserve/proof rules; a deliberately weaker mock must be identified as a separate simulation and cannot claim to satisfy the invariants. This flags an ambiguity, not a proposal to weaken I-7/I-8/I-13.
2. **Define boundary and pending-exit accounting.** I-2's equation describes private transfers, while deposits, withdrawals, public fees, and unpaid exit entitlements need explicit state-transition equations. Keep I-1/I-2 unchanged; add those equations to a later proof-statement specification so consuming a note into an unpaid exit cannot hide an outstanding liability.
3. **Separate inclusion from spent-state checks.** `docs/ARCHITECTURE.md` lists input-not-spent among proof facts. Specify which part proves authenticated non-membership/update and which part rejects public duplicate nullifiers. A membership proof alone does not establish unspent status. Historical note anchors, if allowed, differ from stale settlement/nullifier roots.
4. **Make asynchronous execution claims conditional.** Candidate C may reduce operation latency and amortize proving, but settled balances/exits still require proofs. Replace any implication that a based app eliminates all shared-state contention with measured claims; its settlement covenant still advances serialized state.
5. **Do not preselect the scaling path.** The upstream notes now keep vProgs conditional. Keep the same neutrality in future architecture/roadmap edits; sharding and shared runtimes should earn their complexity through benchmarks and recovery results.
6. **Recovery requires data, not just a root.** Define what is retained in L1 history, replicated archives, wallet backups, and independent software, including pruning and reorg policy. A clean prover rebuild and valid exit are separate from safely rejecting unverifiable state. I-9 does not waive I-10.
7. **Specify prover confidentiality.** State whether proving is local or whether a service learns plaintext notes/amounts/witnesses. A zero-knowledge proof's public confidentiality does not automatically hide inputs from its prover. Candidate C must also explain confidential execution and public resource-access leakage.
8. **Use measured safety/privacy language.** README's trustless destination is an aspiration; describe it as a target and keep the current research disclaimer. RAILGUN's "proven product pattern" and roadmap phrases such as "prove safety" should refer to design experience or demonstrated test properties, not mathematical or cryptographic correctness. No test suite establishes the full invariants by itself.
9. **Resolve licensing before inviting reuse/contributions.** Choose and add the canonical license, and clarify documentation/code coverage in README. `LICENSING.md` acknowledges the gap, but postponing it until substantial code arrives leaves publication/reuse intentions unclear. No license was selected on the steward's behalf.
10. **Prepare publication tooling.** Establish the Git repository and intended remote; create required labels before converting backlog entries to actual issues. The `#1`–`#15` headings are proposal ordinals, not existing GitHub issue numbers. Consider calling them proposal IDs. Add lightweight Markdown/link checks after deciding how external failures are handled; no code-test framework is needed yet.

The private security contact and independent-review process are appropriately future requirements at this documentation-only stage. Establish them before any deployed code carries economic value, as `SECURITY.md` already requires.

## Proposed research direction for review

Investigate A as the smallest falsifiable settlement experiment, while retaining B and C. Before accepting ADR-0001, resolve its proof-statement, data-recovery, and permissionless-exit gates. Do not begin production cryptography, or infer production suitability from a successful testnet round trip.

## Security preservation and adversarial second pass

`SECURITY-INVARIANTS.md` remains byte-for-byte identical to the initial baseline. SHA-256: `135401b1bfbe8adf9122faa1cee075efc4351f9dc48c4abea1dbee0c006c943a`.

The second pass checked whether the proposal could imply unbacked minting, cross-shard/batch duplicate spending, incorrect reserve release, witness/metadata disclosure, dependency loss, stale/reorg replay, or hidden admin authority. ADR-0001 records those risks as validation obligations, and accepts none as a trade-off. The feasibility recommendation introduces no new operational authority, funding path, or implementation.
