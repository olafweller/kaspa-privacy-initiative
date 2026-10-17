# ADR 0010: approved 128M outer classification proof experiment

Date: 2026-10-17. Status: accepted for local research; no production adoption.

## Context and decision

[ADR 0009](0009-accelerated-bn254-qualification.md) qualified a specific accelerated
backend and measured the full unchanged fixture at 117,473,222 user cycles. Its
32M practical target failed, and its larger calibration did not authorize proving.
The owner subsequently explicitly approved a new 128M execution budget and one
real outer-proof attempt, including receipt completion, within 3,600 seconds.

Retain the old research outcomes. Do not retrospectively redefine their success.
Reuse the exact classifier image, circuit/VK/proofs/operation fixtures and point
validation. No guest code, cryptographic arithmetic or setup changes are needed.

The [predeclared plan](../../poc/outer-proof-128m/PLAN.md) fixes CPU, thread,
address-space, aggregate sampled RSS, cycle and wall limits before execution.
Qualify all existing full replay, changed-statement and malformed-then-valid
sequences, plus the narrow authentication/malformed controls, under the new limit.
Then proceed directly to one real succinct receipt with the existing pinned SDK
and prover. On resource/OS/IPC/proving failure, stop and retain the concrete stage.
Do not automatically raise a budget or substitute an easier statement.

## Verification and trust

Use the existing RISC Zero SDK's real prove/verify APIs. Request succinct receipt
production in the same bounded job, including compression/resolution. Supplied
and unresolved assumptions and development mode are forbidden.

Prepare expected program identity and complete journals before qualification and
proof production. Actual cryptographic receipt verification in a separate process
must bind successful exit, the independently expected program, root, initial
state, every native ID/outcome/balance and final state. Reject a changed journal
and wrong expected image through the SDK's actual seal/claim verification.

This reuses the existing [source/reuse review](../../poc/groth16-comparison/SOURCES.md)
and [pinned backend decision](0009-accelerated-bn254-qualification.md). It adds a
bounded host proof harness, not a new cryptographic subsystem or privacy relation.
The synthetic predicate, one-party research setup, fixed local ordering source
and existing note/recovery/native-integration limitations remain unchanged.

## Alternatives and consequence

Further optimization first would postpone the now measurable proof question;
the owner explicitly approved this single attempt. Retaining the 32M cap would
block it by definition. A larger automatic retry or simpler statement would not
answer the approved experiment. An actual receipt closes only this local compact
wallet-classification milestone, not financial privacy or native settlement.

## Outcome

[All 24 qualification cases pass](../../poc/outer-proof-128m/RESULTS.md). One real
succinct-proof job is stopped by the predeclared whole-group wall watchdog at
3,600 seconds without returning a candidate or completed receipt. No retry or
budget increase follows. Receipt verification entry points are implemented but
cannot be exercised without a receipt. Full execution qualification is closed;
actual practical outer-proof production and separate seal verification remain
open. CPU/RSS, cgroup pressure, source and exact last-stage evidence are retained.

An owner-resumed [bounded follow-up](../../poc/proof-phase-diagnostics/RESULTS.md)
separately proves two retained segments, lifts and joins them, and independently
verifies all five partial receipts. This does not revise the one-hour full-job
outcome or the original 32M target; full-classifier proving remains open.
