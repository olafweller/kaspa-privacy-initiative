# A1 S0 trials — 2026-10-08

See the [plain-English report](../../../../docs/poc-a1-s0-trials-2026-10-08.md)
and [public record](public-record.json). This is a newly constructed summary of
selected public receipt fields: transaction IDs, integer-sompi amounts, UTC
times, hashes and the scoped outcomes. It is not an export of operator files.

`SHA256SUMS` binds the two files in this directory. Transaction `full_hash`
uses Kaspa's Full-body hash; it is distinct from a SHA-256 file checksum.
Intent times precede SDK/RPC submission and do not measure network arrival.
Observation intervals are monotonic seconds between successful checks, not
a claim of continuous monitoring or permanent finality.

Raw Full histories and validation records remain with the operator. The
summary is not a self-contained cryptographic or chain-acceptance proof.
Acceptance can be checked separately against TN10 history; C-node trust and
single-party setup are unchanged. No claim secrets, recovery material,
credentials, infrastructure bindings, wallet files or operator logs are included.
