"""Fixed five-proof workload. No provider credentials or arbitrary commands."""
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tarfile
import threading
import time

from common import atomic, sha

PHASES = [('segment-24', 900, ['segment', '24']), ('lift-24', 450, ['lift', '24']),
          ('segment-25', 900, ['segment', '25']), ('lift-25', 450, ['lift', '25']),
          ('join', 600, ['join'])]
MEMORY = 12*1024**3
CPU_COUNT = 4


def gpu_query(arguments):
    result = subprocess.run(['nvidia-smi', *arguments, '--format=csv,noheader,nounits'],
                            capture_output=True, text=True, timeout=5, check=True)
    return [line.split(', ') for line in result.stdout.strip().splitlines() if line.strip()]


def hardware():
    rows = gpu_query(['--query-gpu=name,uuid,memory.total,driver_version,compute_cap'])
    assert len(rows) == 1 and rows[0][0] == 'NVIDIA L40S', 'one L40S required'
    assert float(rows[0][2]) >= 45000 and rows[0][4] == '8.9'
    assert not gpu_query(['--query-compute-apps=pid,gpu_uuid,used_gpu_memory'])
    limits = {}
    for name in ('cpu.max', 'memory.max', 'cpuset.cpus.effective'):
        try:
            limits[name] = (Path('/sys/fs/cgroup')/name).read_text().strip()
        except OSError:
            limits[name] = None  # Do not invent a cgroup limit on unsupported hosts.
    return {'name': rows[0][0], 'uuid': rows[0][1], 'vramMiB': float(rows[0][2]),
            'driverVersion': rows[0][3], 'computeCapability': rows[0][4],
            'cgroupV2Limits': limits, 'availableCpuAffinity': sorted(os.sched_getaffinity(0))}


def process_sample(group, counters):
    rss = vms = threads = 0
    pids = []
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():
            continue
        try:
            f = (path/'stat').read_text().rsplit(')', 1)[1].split()
            if int(f[2]) != group or f[0] == 'Z':
                continue
            pids.append(int(path.name))
            key = (int(path.name), int(f[19]))
            old = counters.get(key, (0, 0))
            counters[key] = (max(old[0], int(f[11])), max(old[1], int(f[12])))
            rss += max(0, int(f[21]))*os.sysconf('SC_PAGE_SIZE')
            vms += int(f[20])
            threads += int(f[17])
        except (OSError, ValueError, IndexError):
            pass
    return rss, vms, threads, pids


def kill(group):
    try:
        os.killpg(group, signal.SIGKILL)
    except ProcessLookupError:
        pass


def run_phase(command, limit, prefix, deadline, cuda, gpu_uuid):
    assert time.monotonic() < deadline, 'aggregate deadline already expired'
    cpus = sorted(os.sched_getaffinity(0))[:CPU_COUNT]
    assert len(cpus) == CPU_COUNT and 'RISC0_DEV_MODE' not in os.environ
    allowed = ('PATH', 'HOME', 'LD_LIBRARY_PATH', 'LANG', 'TZ',
               'NVIDIA_VISIBLE_DEVICES', 'NVIDIA_DRIVER_CAPABILITIES')
    env = {k: os.environ[k] for k in allowed if k in os.environ}
    env.update({'RISC0_PROVER': 'ipc', 'RISC0_SERVER_PATH': os.environ['RISC0_SERVER_PATH'],
                'RAYON_NUM_THREADS': '4', 'OMP_NUM_THREADS': '4', 'OPENBLAS_NUM_THREADS': '4',
                'CUDA_VISIBLE_DEVICES': '0', 'CUDA_CACHE_PATH': str(prefix.parent/'cuda-cache'),
                'RUST_LOG': 'info'})
    started = time.monotonic()
    own_cpu = {}
    peak_rss = peak_vms = peak_vram = 0
    gpu_evidence = False
    failure = None
    atomic(prefix.with_suffix('.started.json'), {'command': command, 'phaseSecondsLimit': limit,
           'unixSeconds': time.time(), 'cpuAffinity': cpus, 'addressSpaceLimit': None,
           'rssStopBytes': MEMORY, 'cudaRequired': cuda})
    with prefix.with_suffix('.stdout.log').open('xb') as stdout, \
            prefix.with_suffix('.stderr.log').open('xb') as stderr, \
            prefix.with_suffix('.samples.jsonl').open('x') as samples:
        child = subprocess.Popen(['taskset', '--cpu-list', ','.join(map(str, cpus)), *command],
                                 env=env, stdin=subprocess.DEVNULL, stdout=stdout,
                                 stderr=stderr, start_new_session=True)
        expired = threading.Event()
        def timeout():
            expired.set()
            kill(child.pid)
        timer = threading.Timer(max(0, min(started+limit, deadline)-time.monotonic()), timeout)
        timer.start()  # Independent of slow telemetry calls and HTTP polling.
        try:
            while True:
                now = time.monotonic()
                rss, vms, threads, pids = process_sample(child.pid, own_cpu)
                peak_rss, peak_vms = max(peak_rss, rss), max(peak_vms, vms)
                active = []
                utilization = None
                if cuda:
                    try:
                        raw = gpu_query(['--query-compute-apps=pid,gpu_uuid,used_gpu_memory'])
                        device = gpu_query(['--query-gpu=uuid,utilization.gpu,memory.used'])
                        utilization = float(next(x[1] for x in device if x[0] == gpu_uuid))
                        for pid, uuid, memory in raw:
                            if uuid == gpu_uuid and int(pid) in pids:
                                active.append({'pid': int(pid), 'gpuUuid': uuid, 'vramMiB': float(memory)})
                        peak_vram = max(peak_vram, sum(x['vramMiB'] for x in active))
                        gpu_evidence |= bool(active) and utilization > 0
                    except (subprocess.SubprocessError, ValueError, StopIteration, OSError):
                        pass  # Missing telemetry never becomes a successful CUDA claim.
                samples.write(json.dumps({'seconds': now-started, 'summedRssBytes': rss,
                    'summedVirtualBytes': vms, 'threads': threads, 'groupPids': pids,
                    'matchingGpuProcesses': active, 'gpuDeviceUtilizationPercent': utilization})+'\n')
                samples.flush()
                if now >= deadline:
                    failure = 'aggregate-or-lease-deadline'
                elif now-started >= limit:
                    failure = 'phase-wall-time'
                elif rss > MEMORY:
                    failure = 'summed-process-rss'
                if expired.is_set():
                    failure = 'aggregate-or-lease-deadline' if deadline <= started+limit else 'phase-wall-time'
                if failure:
                    kill(child.pid)
                pid, status, usage = os.wait4(child.pid, os.WNOHANG)
                if pid:
                    break
                time.sleep(0.2)
        finally:
            timer.cancel()
            kill(child.pid)
    child.returncode = os.waitstatus_to_exitcode(status)
    if cuda and not gpu_evidence and failure is None:
        failure = 'cuda-process-activity-not-established'
    ticks = os.sysconf('SC_CLK_TCK')
    report = {'exitCode': child.returncode, 'failure': failure,
              'wallSeconds': time.monotonic()-started, 'phaseSecondsLimit': limit,
              'peakSampledSummedRssBytes': peak_rss, 'peakSampledSummedVirtualBytes': peak_vms,
              'peakMatchingGpuProcessVramMiB': peak_vram, 'gpuProcessActivityObserved': gpu_evidence,
              'kernelWaitUserSeconds': usage.ru_utime, 'kernelWaitSystemSeconds': usage.ru_stime,
              'sampledOwnCpuSeconds': sum(sum(v) for v in own_cpu.values())/ticks,
              'cpuAffinity': cpus, 'computeThreads': 4,
              'note': 'CPU/RSS/VRAM are sampled; sums may double-count shared memory and miss peaks. GPU PID namespace mismatch makes qualification inconclusive.'}
    atomic(prefix.with_suffix('.resources.json'), report)
    return report


def check_inputs(package, policy):
    for name, spec in policy['inputs'].items():
        data = (package/'inputs'/name).read_bytes()
        assert len(data) == spec['bytes'] and sha(data) == spec['sha256']
    assert sha((package/'bin/kpi-takeover-host').read_bytes()) == policy['cpuVerifierSha256']


def snapshot(output):
    allowed = []
    for p in output.rglob('*'):
        if p.is_file() and not p.is_symlink() and 'cuda-cache' not in p.parts:
            if p.suffix in ('.bin', '.bincode', '.json', '.jsonl', '.log'):
                allowed.append(p)
    destination = output/'artifacts.tar.gz'
    temp = output/'artifacts.tmp'
    with tarfile.open(temp, 'w:gz') as archive:
        for p in sorted(allowed):
            data = p.read_bytes()
            item = tarfile.TarInfo(p.relative_to(output).as_posix())
            item.size, item.mode = len(data), 0o644
            archive.addfile(item, io.BytesIO(data))
    os.replace(temp, destination)
    return {'sha256': sha(destination.read_bytes()), 'bytes': destination.stat().st_size}


def execute(package, output, lease, update):
    started = time.monotonic()
    remaining = lease['stopUnix']-time.time()-60
    assert remaining > 0
    deadline = started+min(3600, remaining)
    policy = json.loads((package/'workload.json').read_text())
    check_inputs(package, policy)
    assert Path('/workspace').is_mount(), 'persistent /workspace mount not observed'
    output.mkdir()
    shutil.copytree(package/'inputs', output/'assets')
    before = time.monotonic()
    gpu = hardware()
    assert time.monotonic()-started < 120
    binary = Path(os.environ['RISC0_SERVER_PATH'])
    build = json.loads((package/'cuda-build.json').read_text())
    assert sha(binary.read_bytes()) == build['binarySha256'] and build['features'] == ['cuda', 'disable-dev-mode']
    atomic(output/'hardware.json', {**gpu, 'driverCheckSeconds': time.monotonic()-before,
           'serverStartupSecondsToHardwareReady': time.monotonic()-started, 'cudaBuild': build,
           'firstUseJitNote': 'Any first-use kernel JIT is included in the first proof API phase, not independently timed.'})
    host = str(package/'bin/kpi-takeover-host')
    for phase, limit, command in PHASES+[('compare', 120, ['compare'])]:
        update({'state': 'running', 'phase': phase})
        arguments = [host, 'phase-diagnostics', command[0], str(output/'assets'), *command[1:]]
        report = run_phase(arguments, limit, output/phase, deadline, phase != 'compare', gpu['uuid'])
        if report['exitCode'] != 0 or report['failure']:
            raise RuntimeError('phase failed: '+phase)
        if phase != 'compare':
            checkpoint = json.loads((output/'assets'/f'{phase}-verified.json').read_text())
            assert checkpoint['claimDigest'] == policy['cpuClaims'][phase], 'CPU claim mismatch'
        update({'state': 'running', 'phase': phase, 'lastCompleted': phase, 'artifact': snapshot(output)})
    assert time.monotonic() < deadline, 'aggregate deadline exceeded'
    atomic(output/'complete.json', {'scope': 'CUDA_PARTIAL_QUALIFICATION_NOT_FULL_CLASSIFIER',
           'seconds': time.monotonic()-started, 'fiveClaimsMatchCpu': True})
    update({'state': 'completed', 'phase': 'done', 'artifact': snapshot(output)})
