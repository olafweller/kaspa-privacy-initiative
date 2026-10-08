"""Isolated exact TN10 terminal relay mechanics; NO network implementation/CLI.

REQUIRED trusted C adapters are not implemented here: native/reference verification,
current lineage/witness/context, fee policy, phase authorization and continuous A
absence. Callers supplying those adapters are trusted code, never B request data.
Passing these tests proves neither cryptographic correctness nor live readiness.
"""
from dataclasses import dataclass
import fcntl
import hashlib
import json
import math
import os
import re
import stat
import time

MAX_BYTES = 65536
HASH = re.compile(r"[0-9a-f]{64}\Z")
UINT = re.compile(r"(?:0|[1-9][0-9]*)\Z")
_TOKEN = object()


class Rejected(ValueError):
    pass


class RPCRejected(Exception):
    """Adapter may raise ONLY for a definite upstream rejection, never timeout."""


def require(ok, message):
    if not ok:
        raise Rejected(message)


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    require(isinstance(raw, bytes) and len(raw) <= MAX_BYTES, "JSON byte budget")
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, "duplicate JSON key")
            out[key] = value
        return out
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(Rejected("nonfinite JSON")))


def snapshot(value):
    return strict_json(encode(value))


def keys(value, expected, message):
    require(type(value) is dict and set(value) == set(expected.split()), message)


def uint(value, bits=64, *, string=False):
    if string:
        require(type(value) is str and UINT.fullmatch(value) is not None, "canonical decimal")
        value = int(value)
    require(type(value) is int and 0 <= value < (1 << bits), "unsigned integer range")
    return value


def hex_bytes(value, size=None):
    require(type(value) is str and len(value) % 2 == 0 and
            re.fullmatch(r"[0-9a-f]*", value) is not None, "canonical lowercase hex")
    raw = bytes.fromhex(value)
    require(size is None or len(raw) == size, "hex length")
    return raw


def hash_value(value):
    require(type(value) is str and HASH.fullmatch(value) is not None, "hash encoding")
    return value


def timestamp(value):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0, "timestamp")
    return value


def point(value):
    keys(value, "transactionId index", "outpoint fields")
    hash_value(value["transactionId"])
    uint(value["index"], 32)


def entry(value):
    keys(value, "amount scriptPublicKey blockDaaScore isCoinbase covenantId", "entry fields")
    uint(value["amount"], string=type(value["amount"]) is str)
    uint(value["blockDaaScore"], string=type(value["blockDaaScore"]) is str)
    require(value["isCoinbase"] is False and value["covenantId"] is None, "entry metadata")
    require(len(hex_bytes(value["scriptPublicKey"])) >= 2, "entry SPK version")


def candidate_equivalence(candidate, canonical_body):
    """Compare supplied pinned-SDK wire with decoded bytes; no new serializer.

    canonical_body must be the trusted, source-pinned existing a1_recovery function.
    Native/reference txid/full-hash/current-context validation is additionally
    required in the trusted validator; byte equivalence is not proof validation.
    """
    require(callable(canonical_body), "trusted canonical-body adapter required")
    keys(candidate, "decoded request params sdk_receipt_sha256 g5_result_sha256", "candidate fields")
    tx, request, params = candidate["decoded"], candidate["request"], candidate["params"]
    keys(tx, "version id inputs outputs lockTime subnetworkId gas payload storageMass", "decoded fields")
    keys(request, "transaction entry", "decoded request fields")
    require(request["transaction"] == tx, "decoded request/body mismatch")
    entry(request["entry"])
    keys(params, "transaction allowOrphan", "submit envelope")
    require(params["allowOrphan"] is False, "orphan policy")
    wire = params["transaction"]
    keys(wire, "version gas lockTime mass storageMass inputs outputs payload subnetworkId verboseData", "SDK wire fields")
    require(tx["version"] == wire["version"] == 1 and type(tx["version"]) is int and
            type(wire["version"]) is int, "terminal version")
    hash_value(tx["id"])
    require(wire["verboseData"] is None, "wire verbose metadata")
    require(type(tx["inputs"]) is list and type(tx["outputs"]) is list and
            len(tx["inputs"]) == len(tx["outputs"]) == 1 and
            type(wire["inputs"]) is list and type(wire["outputs"]) is list and
            len(wire["inputs"]) == len(wire["outputs"]) == 1, "single terminal input/output")
    for name in ("lockTime", "gas", "storageMass"):
        require(uint(tx[name], string=True) == uint(wire[name]), "wire integer mismatch")
    require(uint(wire["mass"]) == uint(wire["storageMass"]), "wire mass mismatch")
    for name, size in (("subnetworkId", 20), ("payload", None)):
        hex_bytes(tx[name], size)
        require(tx[name] == wire[name], "wire envelope mismatch")
    a, b = tx["inputs"][0], wire["inputs"][0]
    keys(a, "previousOutpoint signatureScript sequence sigOpCount computeBudget", "decoded input fields")
    keys(b, "previousOutpoint signatureScript sequence sigOpCount computeBudget verboseData", "wire input fields")
    point(a["previousOutpoint"]); point(b["previousOutpoint"])
    require(a["previousOutpoint"] == b["previousOutpoint"] and b["verboseData"] is None, "wire input point/metadata")
    hex_bytes(a["signatureScript"])
    require(a["signatureScript"] == b["signatureScript"], "wire witness mismatch")
    require(uint(a["sequence"], string=True) == uint(b["sequence"]) == (1 << 64) - 1, "terminal sequence")
    require(uint(a["sigOpCount"], 8) == uint(b["sigOpCount"], 8) == 0, "terminal sigop")
    require(uint(a["computeBudget"], 16) == uint(b["computeBudget"], 16), "wire budget mismatch")
    a, b = tx["outputs"][0], wire["outputs"][0]
    keys(a, "value scriptPublicKey covenant", "decoded output fields")
    keys(b, "value scriptPublicKey covenant verboseData", "wire output fields")
    require(uint(a["value"], string=True) == uint(b["value"]), "wire payout mismatch")
    spk = hex_bytes(a["scriptPublicKey"])
    require(len(spk) >= 2, "payout SPK version")
    require(b["scriptPublicKey"] == a["scriptPublicKey"], "pinned SDK wire payout SPK mismatch")
    require(a["covenant"] is None and b["covenant"] is None and b["verboseData"] is None, "terminal payout metadata")
    require(canonical_body(tx) == canonical_body(wire), "pinned canonical bytes mismatch")
    hash_value(candidate["sdk_receipt_sha256"]); hash_value(candidate["g5_result_sha256"])


QUAL_FIELDS = "directory_binding_sha256 witness_contract schema run_id base_instance_id network mode phase authorized g5_pass txid full_hash decoded_sha256 params_sha256 sdk_receipt_sha256 g5_result_sha256 exact_input exact_entry exact_payout fee_sompi authorization_sha256 sources_sha256 witness_sha256 native_current_sha256 fee_policy_sha256 absence_sha256 qualified_at expires_at witness_at absence_at loss_at lineage_active current_input_unspent native_full_valid current_native_full_valid fee_policy_passed continuous_A_absence"


@dataclass(frozen=True)
class ValidatedIntent:
    candidate_bytes: bytes
    qualification_bytes: bytes
    intent_bytes: bytes
    validated_wall: float
    validated_monotonic: float
    token: object

    @property
    def digest(self):
        return sha(self.intent_bytes)


def validate_intent(candidate, trusted_validator, canonical_body, directory_binding, *, clock=time.time, monotonic=time.monotonic):
    """Eligibility comes exclusively from trusted C callback, never B flags."""
    require(callable(trusted_validator), "trusted C qualification adapter required")
    began = monotonic(); wall_started = timestamp(clock())
    binding = snapshot(directory_binding)
    c = snapshot(candidate)
    candidate_equivalence(c, canonical_body)
    before = encode(c)
    q = snapshot(trusted_validator(c, snapshot(binding)))
    now = timestamp(clock()); finished_mono = monotonic()
    require(now + 2 >= wall_started and 0 <= finished_mono - began <= 60 and
            abs((now - wall_started) - (finished_mono - began)) <= 1, "validation clock/deadline")
    require(encode(c) == before, "validator mutated candidate")
    keys(q, QUAL_FIELDS, "trusted qualification fields")
    require(q["schema"] == "kpi-C-terminal-qualification/v1" and q["network"] == "testnet-10" and
            q["mode"] in {"live","finite-live-native"} and q["phase"] == "G6-terminal", "terminal phase/network")
    for name in ("run_id", "base_instance_id"):
        require(type(q[name]) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", q[name]) is not None, "run identity")
    for name in ("authorized", "g5_pass", "lineage_active", "current_input_unspent", "native_full_valid",
                 "current_native_full_valid", "fee_policy_passed", "continuous_A_absence"):
        require(q[name] is True, "trusted prerequisite rejected: " + name)
    for name in ("txid", "full_hash", "decoded_sha256", "params_sha256", "sdk_receipt_sha256", "g5_result_sha256",
                 "authorization_sha256", "sources_sha256", "witness_sha256", "native_current_sha256", "fee_policy_sha256", "absence_sha256"):
        hash_value(q[name])
    require(q["directory_binding_sha256"] == sha(encode(binding)), "trusted directory binding")
    require(q["witness_contract"] == "finite-prefix-current-witness/v1", "distinct witness contract required")
    for name in ("run_id", "base_instance_id", "authorization_sha256", "sources_sha256"):
        require(q[name] == binding[name], "directory run/authority mismatch")
    tx = c["decoded"]
    require(q["txid"] == tx["id"] and q["decoded_sha256"] == sha(encode(tx)) and
            q["params_sha256"] == sha(encode(c["params"])) and
            q["sdk_receipt_sha256"] == c["sdk_receipt_sha256"] and
            q["g5_result_sha256"] == c["g5_result_sha256"], "native/SDK/G5/body binding")
    point(q["exact_input"]); entry(q["exact_entry"])
    require(q["exact_input"] == tx["inputs"][0]["previousOutpoint"] and
            q["exact_entry"] == c["request"]["entry"] and q["exact_payout"] == tx["outputs"][0], "current input/payout binding")
    fee = uint(q["fee_sompi"], string=True)
    require(uint(q["exact_entry"]["amount"], string=type(q["exact_entry"]["amount"]) is str) - uint(q["exact_payout"]["value"], string=True) == fee,
            "explicit value/fee conservation")
    for name in ("qualified_at", "expires_at", "witness_at", "absence_at", "loss_at"):
        timestamp(q[name])
    require(-2 <= now - q["qualified_at"] <= 15 and now < q["expires_at"] and
            -2 <= now - q["witness_at"] <= 15 and -2 <= now - q["absence_at"] <= 5 and
            q["loss_at"] <= q["absence_at"], "stale/future qualification")
    intent = {"schema": "kpi-exact-terminal-intent/v1", "candidate": c, "qualification": q}
    return ValidatedIntent(before, encode(q), encode(intent), now, finished_mono, _TOKEN)


def _open_directory(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    s = os.fstat(fd)
    try:
        require(s.st_uid == os.getuid() and stat.S_IMODE(s.st_mode) == 0o700, "private directory owner/mode")
    except BaseException:
        os.close(fd)
        raise
    return fd


def _exists(dfd, name):
    try:
        os.stat(name, dir_fd=dfd, follow_symlinks=False)
        return True
    except FileNotFoundError:
        return False


def _new(dfd, name, value):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dfd)
    with os.fdopen(fd, "wb") as f:
        f.write(encode(value)); f.flush(); os.fsync(f.fileno())
    os.fsync(dfd)


def submit_once(directory, candidate, trusted_validator, canonical_body, rpc_factory, *, clock=time.time, monotonic=time.monotonic):
    """One fsynced claim -> at most one submit, including restart/concurrency.

    No retries, even for definite rejection. An existing/partial/foreign claim
    reserves the attempt and demands independent exact reconciliation. Callbacks
    must be trusted, source-qualified C code; this module provides none of them.
    """
    require(callable(rpc_factory), "explicit trusted RPC adapter required")
    began = monotonic(); wall_started = timestamp(clock())
    dfd = _open_directory(directory)
    lockfd = None
    try:
        lockfd = os.open("terminal.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=dfd)
        s = os.fstat(lockfd)
        require(stat.S_ISREG(s.st_mode) and s.st_uid == os.getuid() and stat.S_IMODE(s.st_mode) == 0o600 and s.st_nlink == 1,
                "private lock binding")
        fcntl.flock(lockfd, fcntl.LOCK_EX)
        if _exists(dfd, "submission-claimed.json"):
            return {"outcome": "already-claimed-reconcile-only", "rpc_calls": 0, "retry": False}
        require(not _exists(dfd, "submission-result.json") and not _exists(dfd, "intent.json"), "partial/foreign namespace; halt")
        bindingfd = os.open("directory-authorization.json", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dfd)
        with os.fdopen(bindingfd, "rb") as f:
            bs = os.fstat(f.fileno())
            require(stat.S_ISREG(bs.st_mode) and bs.st_uid == os.getuid() and
                    stat.S_IMODE(bs.st_mode) == 0o600 and bs.st_nlink == 1, "directory authorization file")
            binding = strict_json(f.read(MAX_BYTES + 1))
        keys(binding, "run_id base_instance_id authorization_sha256 sources_sha256 device inode owner", "directory authorization fields")
        ds = os.fstat(dfd)
        require(binding["device"] == ds.st_dev and binding["inode"] == ds.st_ino and
                binding["owner"] == ds.st_uid, "held directory identity mismatch")
        intent = validate_intent(candidate, trusted_validator, canonical_body, binding, clock=clock, monotonic=monotonic)
        q = strict_json(intent.qualification_bytes)
        # Exact bytes are copied/frozen before persistence and never read from B again.
        _new(dfd, "intent.json", strict_json(intent.intent_bytes))
        _new(dfd, "submission-claimed.json", {"schema": "kpi-terminal-claimed/v1", "intent_sha256": intent.digest,
             "txid": q["txid"], "full_hash": q["full_hash"], "params_sha256": q["params_sha256"],
             "authorization_sha256": q["authorization_sha256"], "sources_sha256": q["sources_sha256"],
             "run_id": q["run_id"], "one_attempt_only": True})
        # If the process dies here, the durable claim forbids all resubmission.
        params = strict_json(intent.candidate_bytes)["params"]
        result = {"intent_sha256": intent.digest, "txid": q["txid"], "full_hash": q["full_hash"], "retry": False}
        rpc = None
        last_wall, last_mono = wall_started, began
        def fresh_before_send():
            nonlocal last_wall, last_mono
            current = timestamp(clock()); current_mono = monotonic()
            require(current + 2 >= last_wall and current_mono >= last_mono and 0 <= current_mono - began <= 60, "attempt clock/deadline")
            last_wall, last_mono = current, current_mono
            elapsed_mono = current_mono - intent.validated_monotonic
            require(elapsed_mono >= 0 and
                    abs((current - intent.validated_wall) - elapsed_mono) <= 1, "dispatch wall/monotonic disagreement")
            require(intent.validated_wall - q["qualified_at"] + elapsed_mono <= 15 and
                    intent.validated_wall - q["witness_at"] + elapsed_mono <= 15 and
                    intent.validated_wall - q["absence_at"] + elapsed_mono <= 5 and
                    intent.validated_wall + elapsed_mono < q["expires_at"], "monotonic qualification expiry")
            require(-2 <= current - q["qualified_at"] <= 15 and current < q["expires_at"] and
                    -2 <= current - q["witness_at"] <= 15 and -2 <= current - q["absence_at"] <= 5,
                    "expired qualification after claim; no submit")
            ds2 = os.fstat(dfd)
            actual = os.stat(directory, follow_symlinks=False)
            require((ds2.st_dev, ds2.st_ino) == (actual.st_dev, actual.st_ino) and
                    actual.st_uid == os.getuid() and stat.S_IMODE(actual.st_mode) == 0o700, "directory path replaced")
            authfd = os.open("directory-authorization.json", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dfd)
            with os.fdopen(authfd, "rb") as f:
                current_binding = strict_json(f.read(MAX_BYTES + 1))
            require(encode(current_binding) == encode(binding), "directory authority replaced")
        try:
            fresh_before_send()  # after both file+directory fsyncs
            rpc = rpc_factory()
            fresh_before_send()  # after connection, immediately before dispatch
            response = snapshot(rpc.call("submitTransaction", params))
            result["response"] = response
            result["outcome"] = "admission-only" if type(response) is dict and response.get("transactionId") == q["txid"] else "ambiguous-reconcile-only"
        except Rejected:
            result["outcome"] = "expired-or-binding-changed-after-claim-reconcile-only"
        except RPCRejected:
            result["outcome"] = "rejected-no-retry"
        except Exception:
            # Do not retain adapter exception strings, which may contain secrets.
            result["outcome"] = "ambiguous-reconcile-only"
        finally:
            if rpc is not None:
                try:
                    rpc.close()
                except Exception:
                    pass
        _new(dfd, "submission-result.json", result)
        return result
    finally:
        if lockfd is not None:
            os.close(lockfd)
        os.close(dfd)


OBS_FIELDS = "observer_epoch observed_monotonic schema run_id network authorization_sha256 sources_sha256 witness_sha256 absence_sha256 at loss_at absence_through absence_scope continuous_A_absence phase_authorized synced lineage_active conflicting_spend reorg observed_txid observed_full_hash accepted_body accepting_block_hash accepting_blue_score current_blue_score exact_input input_unspent payout_outpoint payout_entry"


@dataclass(frozen=True)
class VerifiedObservation:
    intent_sha256: str
    evidence_bytes: bytes
    token: object


def observe(intent, raw_evidence, trusted_observer, canonical_body, *, clock=time.time, monotonic=time.monotonic, initial=None):
    """Pure decision over C-authenticated observations; no network/chain storage.

    trusted_observer must verify independent accepted-chain membership/body,
    current source/payout UTXOs and the original dispatch absence samples.
    A returning after submission cannot invalidate an already accepted payout.
    B-supplied booleans are never interpreted here as independent evidence.
    Native acceptance verification remains unintegrated. Returned observations
    are pure decisions, not durable receipts or whole-G6 success.
    """
    require(isinstance(intent, ValidatedIntent) and intent.token is _TOKEN, "validated intent required")
    require(callable(trusted_observer) and callable(canonical_body), "trusted observation adapters required")
    began = monotonic(); wall_started = timestamp(clock())
    q, c = strict_json(intent.qualification_bytes), strict_json(intent.candidate_bytes)
    e = snapshot(trusted_observer(snapshot(raw_evidence)))
    now = timestamp(clock()); finished_mono = monotonic()
    require(now + 2 >= wall_started and 0 <= finished_mono - began <= 60 and
            abs((now-wall_started)-(finished_mono-began)) <= 1, "observation clock/deadline")
    keys(e, OBS_FIELDS, "trusted observation fields")
    timestamp(e["observed_monotonic"])
    require(type(e["observer_epoch"]) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}",e["observer_epoch"]) is not None,
            "authenticated C observer lifetime required")
    require(e["schema"] == "kpi-C-terminal-observation/v1" and e["network"] == "testnet-10" and
            e["run_id"] == q["run_id"] and e["authorization_sha256"] == q["authorization_sha256"] and
            e["sources_sha256"] == q["sources_sha256"], "observation phase/source binding")
    for name in ("authorization_sha256", "sources_sha256", "witness_sha256", "absence_sha256", "observed_txid", "observed_full_hash", "accepting_block_hash"):
        hash_value(e[name])
    for name in ("continuous_A_absence", "phase_authorized", "synced", "lineage_active"):
        require(e[name] is True, "observation prerequisite: " + name)
    require(e["conflicting_spend"] is False and e["reorg"] is False and e["input_unspent"] is False, "conflict/reorg/source remains unspent")
    for name in ("at", "loss_at", "absence_through"):
        timestamp(e[name])
    require(-2 <= now - e["at"] <= 15 and e["loss_at"] == q["loss_at"] and
            e["absence_scope"] == "dispatch-qualification" and e["absence_through"] == q["absence_at"] and
            e["absence_sha256"] == q["absence_sha256"] and
            -2 <= q["qualified_at"] - e["absence_through"] <= 5, "observation freshness/original dispatch absence interval")
    require(e["observed_txid"] == q["txid"] and e["observed_full_hash"] == q["full_hash"] and
            canonical_body(e["accepted_body"]) == canonical_body(c["decoded"]), "exact accepted native body/hash")
    point(e["exact_input"]); point(e["payout_outpoint"]); entry(e["payout_entry"])
    require(e["exact_input"] == q["exact_input"] and e["payout_outpoint"] == {"transactionId": q["txid"], "index": 0}, "exact spent/payout outpoints")
    payout = q["exact_payout"]
    require(uint(e["payout_entry"]["amount"], string=type(e["payout_entry"]["amount"]) is str) ==
            uint(payout["value"], string=True) and
            e["payout_entry"]["scriptPublicKey"] == payout["scriptPublicKey"], "exact unspent payout entry")
    uint(e["accepting_blue_score"]); uint(e["current_blue_score"])
    require(e["current_blue_score"] - e["accepting_blue_score"] > 20, "acceptance blue distance")
    if initial is not None:
        require(isinstance(initial, VerifiedObservation) and initial.token is _TOKEN and initial.intent_sha256 == intent.digest, "verified same-intent initial observation")
        old = strict_json(initial.evidence_bytes)
        require(e["observer_epoch"] == old["observer_epoch"], "C observer restarted; reconcile")
        elapsed_mono = e["observed_monotonic"] - old["observed_monotonic"]
        require(e["at"] - old["at"] >= 120 and elapsed_mono >= 120 and
                abs((e["at"]-old["at"])-elapsed_mono) <= 1, "later check before 120 seconds or clock disagreement")
        require(e["accepting_block_hash"] == old["accepting_block_hash"] and
                e["accepting_blue_score"] == old["accepting_blue_score"] and
                e["current_blue_score"] >= old["current_blue_score"], "acceptance changed/blue regressed")
    return VerifiedObservation(intent.digest, encode(e), _TOKEN)
