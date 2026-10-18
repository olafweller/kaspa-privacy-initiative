# Adversarial review of the fixed full-classifier wrapper

The classifier, wallet proof verification, value semantics and fixed statement
are unchanged. No curve arithmetic, wallet setup, deposit/exit/settlement path,
keys or private-note relation is added. Inflation, double spending and reserve
release rules remain those of the previously execution-qualified toy fixture;
this proof does not extend that fixture to a private-payment protocol.

The public PR39 archive is pinned by SHA256 and every member by its archived
manifest. All 24 qualification reports/fixture hashes, expected journals, image,
cycles and resource results are checked again by the existing proof host gate.
A separate CPU-only check command exercises that gate without another proof or
execution run. Incorrect qualification/fixtures cannot authorize a changed
statement. The verifier's only receipt-check change adds actual corrupted-seal
rejection; the old prove implementation and guest remain unchanged.

The full service has a separate static entry point/volume namespace. Its
executor/scope are selected by deployment code, never by an HTTP argument.
Authentication, exact Pod/lease identity, fresh independent heartbeat, time
remaining and durable attempt-once state are retained. Restart cannot retry a
started job. The controller cannot substitute commands, inputs or limits.

The complete proof process group inherits four CPU affinity/compute threads and
the qualified RSS-only memory policy, with an independent 3,600s kill timer;
there is no RLIMIT_AS on the GPU job. B independently enforces the absolute lease
and provider stop even if the job, Cloud or gateway disappears. Failed telemetry
cannot count as CUDA success. Snapshot/download failure cannot extend either
deadline. Fresh state/lease/unit avoids overwriting the completed qualification.

Only public synthetic fixtures are shipped. API account credentials stay on B;
its existing service token is injected to the Pod without logging values.
B root and the GPU rental provider remain trusted operators for these public
fixtures; this setup must not be described as protection for secret witnesses.

Artifacts are treated as untrusted input: original archive hash/size and checked
regular paths, independent expected input hashes, trusted CPU verifier hash,
succinct seal, successful exit, empty assumptions, fixed image and exact full
journal. Wrong-image, five journal mutations and corrupted-seal controls invoke
real cryptographic verification. GPU-written success JSON alone is insufficient.
No live result is claimed until these checks run on a returned full receipt.
