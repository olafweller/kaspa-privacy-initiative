#!/usr/bin/env python3
"""One finite process group with declared CPU, address-space and RSS limits."""
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

seconds, prefix, *command = sys.argv[1:]
seconds = int(seconds)
assert 0 < seconds <= 3600 and command
assert 'RISC0_DEV_MODE' not in os.environ
cpus = {0, 1, 2, 3}
assert cpus <= os.sched_getaffinity(0)
memory = 12 * 1024**3
page_size = os.sysconf('SC_PAGE_SIZE')
env = os.environ | {'RAYON_NUM_THREADS': '4', 'OMP_NUM_THREADS': '4',
                    'OPENBLAS_NUM_THREADS': '4', 'CARGO_BUILD_JOBS': '4'}


def restrict():
    os.sched_setaffinity(0, cpus)
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))


def group_stats(group):
    rss = threads = processes = 0
    for directory in Path('/proc').iterdir():
        if not directory.name.isdigit():
            continue
        try:
            fields = (directory / 'stat').read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) != group:
                continue
            processes += 1
            rss += max(0, int(fields[21])) * page_size
            threads += int(fields[17])
        except (OSError, ValueError, IndexError):
            continue  # A process may exit between enumeration and reading.
    return rss, threads, processes


def kill_group(group):
    try:
        os.killpg(group, signal.SIGKILL)
    except ProcessLookupError:
        pass


started = time.monotonic()
peak_rss = peak_threads = peak_processes = 0
limit_exceeded = None
with Path(prefix + '.stdout.log').open('xb') as out, \
        Path(prefix + '.stderr.log').open('xb') as err, \
        Path(prefix + '.samples.jsonl').open('x') as samples:
    child = subprocess.Popen(command, env=env, stdout=out, stderr=err,
                             start_new_session=True, preexec_fn=restrict)
    last_sample = -5.0
    while True:
        elapsed = time.monotonic() - started
        rss, threads, processes = group_stats(child.pid)
        peak_rss = max(peak_rss, rss)
        peak_threads = max(peak_threads, threads)
        peak_processes = max(peak_processes, processes)
        if elapsed - last_sample >= 5:
            samples.write(json.dumps({'seconds': elapsed, 'summedRssBytes': rss,
                                      'threads': threads, 'processes': processes}) + '\n')
            samples.flush()
            last_sample = elapsed
        if elapsed >= seconds or rss > memory:
            limit_exceeded = 'wall-time' if elapsed >= seconds else 'summed-process-group-rss'
            kill_group(child.pid)
        pid, status, usage = os.wait4(child.pid, os.WNOHANG)
        if pid:
            break
        time.sleep(0.2)
    # Do not leave an IPC/prover descendant running after a parent failure.
    kill_group(child.pid)
code = os.waitstatus_to_exitcode(status)
child.returncode = code
cgroup = {}
for name in ['cpu.max', 'memory.max', 'memory.events']:
    path = Path('/sys/fs/cgroup') / name
    if path.exists():
        cgroup[name] = path.read_text().strip()
report = {
    'command': command, 'secondsBudget': seconds, 'limitExceeded': limit_exceeded,
    'seconds': time.monotonic() - started, 'exitCode': code,
    'cpuAffinity': sorted(cpus), 'rayonThreads': 4, 'ompThreads': 4,
    'perProcessAddressSpaceLimitBytes': memory,
    'summedProcessGroupRssStopThresholdBytes': memory,
    'rssSamplingIntervalSeconds': 0.2, 'peakSampledSummedProcessGroupRssBytes': peak_rss,
    'peakSampledProcessGroupThreads': peak_threads,
    'peakSampledProcessGroupProcesses': peak_processes,
    'kernelWaitUserSeconds': usage.ru_utime, 'kernelWaitSystemSeconds': usage.ru_stime,
    'kernelWaitMaxIndividualProcessRssKiB': usage.ru_maxrss,
    'observedEnvironmentCgroup': cgroup,
    'memoryMeasurementNote': 'Sampled sum can double-count shared pages; not exact physical memory or a cgroup peak.',
}
with Path(prefix + '.resources.json').open('x') as output:
    output.write(json.dumps(report, indent=2) + '\n')
raise SystemExit(124 if limit_exceeded else code)
