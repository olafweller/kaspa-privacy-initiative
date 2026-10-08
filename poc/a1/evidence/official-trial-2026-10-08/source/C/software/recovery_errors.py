"""Private bounded durable diagnostics; never log locals, keys or private inputs."""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import traceback
import threading

_stage = 'startup'
_artifact = None
_secrets = []
_directory = None

def initialize(directory):
    global _directory
    _directory = Path(directory)
    _directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if _directory.is_symlink():
        raise ValueError('diagnostic directory symlink forbidden')

def register_secret(data):
    if not isinstance(data, bytes) or len(data) < 16:
        raise ValueError('invalid diagnostic secret registration')
    _secrets.append(data)

def register_backup(backup):
    for name in ['claim-secret.bin', 'recipient-key.bin']:
        register_secret((Path(backup) / name).read_bytes())

def sanitize(value):
    if isinstance(value, bytes):
        value = value.decode(errors='replace')
    text = str(value)
    for secret in _secrets:
        for form in [secret.hex(), base64.b64encode(secret).decode(), str(secret),
                     json.dumps(list(secret))]:
            text = text.replace(form, '<redacted-secret>')
    # Unknown credential-looking output also gets suppressed; keep public hashes.
    text = re.sub(r'(?i)(claim[_-]?secret|recipient[_-]?private[_-]?key|unlock[_-]?key|ciphertext_b64|nonce_b64)\s*[=:]\s*[^\s,}]+',
                  r'\1=<redacted-secret>', text)
    return text[:8192]

def emit(kind, data):
    if _directory is None:
        directory = os.environ.get('KPI_RECOVERY_DIAGNOSTIC_DIR')
        if not directory:
            raise ValueError('durable diagnostic directory not configured')
        initialize(directory)
    path = _directory / ('process-' + str(os.getpid()) + '.jsonl')
    value = {'schema': 'kpi-recovery-diagnostic/v1', 'at': time.time(), 'monotonic_seconds': time.monotonic(), 'pid': os.getpid(),
             'kind': kind, 'stage': _stage, 'artifact': _artifact, **data}
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode() + b'\n'
    fd = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'ab') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        if os.fstat(f.fileno()).st_size + len(raw) > 8 * 1024 * 1024:
            raise ValueError('diagnostic evidence size limit exceeded')
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    fd = os.open(_directory, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def stage(name, artifact=None):
    global _stage, _artifact
    _stage = name
    _artifact = None if artifact is None else str(artifact)
    emit('stage', {})

def nonsecret_input_hashes(args):
    hashes = {}
    for arg in args[1:]:
        p = Path(str(arg))
        if p.is_file() and p.name not in {'claim-secret.bin', 'recipient-key.bin', 'unlock.key', 'backup-package.json'}:
            hashes[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    return hashes

def command(args, timeout=1200):
    # Register private backup paths before launching anything that can echo them.
    for arg in args:
        p = Path(str(arg))
        if p.name in {'claim-secret.bin', 'recipient-key.bin', 'unlock.key'} and p.is_file():
            register_secret(p.read_bytes())
    hashes = nonsecret_input_hashes(args)
    started = time.monotonic()
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exception:
        emit('child-timeout', {'command': [sanitize(x) for x in args], 'exit_code': None,
             'stdout': sanitize(exception.stdout or ''), 'stderr': sanitize(exception.stderr or ''),
             'nonsecret_input_sha256': hashes})
        raise
    emit('child-exit', {'command': [sanitize(x) for x in args], 'exit_code': result.returncode,
         'stdout': sanitize(result.stdout), 'stderr': sanitize(result.stderr),
         'nonsecret_input_sha256': hashes, 'child_elapsed_seconds': time.monotonic() - started,
         'rust_exception_type': 'RustPanic' if 'panicked at' in result.stderr else
             'RustError' if result.returncode and str(args[0]).endswith(('kpi-poc-a1', 'a1_reference')) else None})
    if result.returncode:
        raise ValueError('child command rejected; exit=' + str(result.returncode) + '; durable child output retained')
    return json.loads(result.stdout)

def capture(exception, child_exit_code=None):
    data = {'exception_type': type(exception).__name__, 'message': sanitize(exception),
            'stack_trace': sanitize(''.join(traceback.format_exception(exception))),
            'child_exit_code': child_exit_code}
    if isinstance(exception, subprocess.CalledProcessError):
        data.update(command=[sanitize(x) for x in exception.cmd], exit_code=exception.returncode,
                    stdout=sanitize(exception.stdout or ''), stderr=sanitize(exception.stderr or ''),
                    nonsecret_input_sha256=nonsecret_input_hashes(exception.cmd))
    emit('exception', data)

def guarded(function):
    try:
        return function()
    except BaseException as exception:
        capture(exception)
        raise

def attach_child(child):
    """Drain pipes with bounded memory; raw output is never written to disk."""
    streams = {}
    for name in ['stdout', 'stderr']:
        pipe = getattr(child, name)
        if pipe is None:
            raise ValueError('diagnostic child stream missing')
        state = {'data': bytearray(), 'truncated': False, 'finished': False}
        def drain(pipe=pipe, state=state):
            try:
                while True:
                    chunk = pipe.read(4096)
                    if not chunk:
                        break
                    remaining = 65536 - len(state['data'])
                    state['data'].extend(chunk[:max(0, remaining)])
                    if len(chunk) > remaining:
                        state['truncated'] = True
            finally:
                state['finished'] = True
        thread = threading.Thread(target=drain, daemon=True)
        thread.start()
        streams[name] = (state, thread)
    return streams

def collect_child(child, streams):
    data = {'command': [sanitize(x) for x in child.args], 'exit_code': child.poll(),
            'nonsecret_input_sha256': nonsecret_input_hashes(child.args)}
    for name, (state, thread) in streams.items():
        thread.join(timeout=2)
        raw = bytes(state['data'])
        # Sanitize before presentation truncation; the collection limit is far
        # beyond the printed prefix, so a secret spanning a read is redacted.
        data[name] = sanitize(raw)
        data[name + '_truncated'] = state['truncated'] or not state['finished']
        if state['finished']:
            getattr(child, name).close()
    emit('supervised-child-exit', data)
