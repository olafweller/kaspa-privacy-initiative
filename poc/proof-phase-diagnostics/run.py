#!/usr/bin/env python3
"""One bounded sequence of supported SDK diagnostics; no proof retries."""
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

MEMORY = 12 * 1024**3
CPUS = {0, 1, 2, 3}
TICKS = os.sysconf('SC_CLK_TCK')
PAGE = os.sysconf('SC_PAGE_SIZE')
CGROUP = Path('/sys/fs/cgroup')


def save(path, value):
    with path.open('x') as output:
        json.dump(value, output, indent=2)
        output.write('\n')


def counters():
    result = {}
    for name in ('memory.events', 'cpu.stat'):
        for line in (CGROUP / name).read_text().splitlines():
            key, value = line.split()
            result[f'{name}:{key}'] = int(value)
    for name in ('cpu.pressure', 'memory.pressure'):
        if not (CGROUP / name).is_file():
            continue
        for line in (CGROUP / name).read_text().splitlines():
            kind, *values = line.split()
            for value in values:
                key, number = value.split('=')
                if key == 'total':
                    result[f'{name}:{kind}:totalMicroseconds'] = int(number)
    return result


def restrict():
    os.sched_setaffinity(0, CPUS)
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY, MEMORY))


def kill(group):
    try:
        os.killpg(group, signal.SIGKILL)
    except ProcessLookupError:
        pass


def observe(group, own_cpu):
    rss = threads = active = 0
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():
            continue
        try:
            fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) != group:
                continue
            key = (int(path.name), int(fields[19]))  # PID plus start clock ticks
            previous = own_cpu.get(key, (0, 0))
            own_cpu[key] = (max(previous[0], int(fields[11])),
                            max(previous[1], int(fields[12])))
            rss += max(0, int(fields[21])) * PAGE
            threads += int(fields[17])
            active += fields[0] not in ('Z', 'X')
        except (OSError, IndexError, ValueError):
            continue
    return rss, threads, active


def phase(command, limit, prefix, deadline):
    started = time.monotonic()
    before = counters()
    own_cpu = {}
    peak_rss = peak_threads = peak_active = 0
    reason = None
    environment = os.environ | {'RAYON_NUM_THREADS': '4', 'OMP_NUM_THREADS': '4',
                                'OPENBLAS_NUM_THREADS': '4', 'CARGO_BUILD_JOBS': '4'}
    save(prefix.with_suffix('.started.json'), {
        'command': command, 'unixSeconds': time.time(), 'phaseSecondsLimit': limit,
        'aggregateSecondsRemaining': max(0, deadline-started),
        'cgroupBefore': before})
    with prefix.with_suffix('.stdout.log').open('xb') as stdout, \
            prefix.with_suffix('.stderr.log').open('xb') as stderr, \
            prefix.with_suffix('.samples.jsonl').open('x') as samples:
        child = subprocess.Popen(command, env=environment, stdout=stdout, stderr=stderr,
                                 start_new_session=True, preexec_fn=restrict)
        try:
            last_sample = -1
            while True:
                now = time.monotonic()
                rss, threads, active = observe(child.pid, own_cpu)
                peak_rss = max(peak_rss, rss)
                peak_threads = max(peak_threads, threads)
                peak_active = max(peak_active, active)
                if now-started-last_sample >= 1:
                    samples.write(json.dumps({
                        'seconds': now-started, 'summedRssBytes': rss,
                        'threads': threads, 'activeProcesses': active,
                        'sampledOwnUserSeconds': sum(v[0] for v in own_cpu.values())/TICKS,
                        'sampledOwnSystemSeconds': sum(v[1] for v in own_cpu.values())/TICKS,
                    })+'\n')
                    samples.flush()
                    last_sample = now-started
                if now >= deadline:
                    reason = 'aggregate-wall-time'
                elif now-started >= limit:
                    reason = 'phase-wall-time'
                elif rss > MEMORY:
                    reason = 'sampled-summed-group-rss'
                if reason:
                    kill(child.pid)
                pid, status, usage = os.wait4(child.pid, os.WNOHANG)
                if pid:
                    break
                time.sleep(0.2)
        finally:
            kill(child.pid)  # Includes IPC descendants when parent fails.
    code = os.waitstatus_to_exitcode(status)
    child.returncode = code
    after = counters()
    result = {
        'command': command, 'exitCode': code, 'limitExceeded': reason,
        'seconds': time.monotonic()-started, 'phaseSecondsLimit': limit,
        'sampledOwnUserSeconds': sum(v[0] for v in own_cpu.values())/TICKS,
        'sampledOwnSystemSeconds': sum(v[1] for v in own_cpu.values())/TICKS,
        'observedProcessIdentities': len(own_cpu),
        'peakSampledSummedRssBytes': peak_rss, 'peakSampledThreads': peak_threads,
        'peakSampledActiveProcesses': peak_active,
        'kernelWaitUserSeconds': usage.ru_utime,
        'kernelWaitSystemSeconds': usage.ru_stime,
        'kernelWaitMaxIndividualProcessRssKiB': usage.ru_maxrss,
        'cgroupBefore': before, 'cgroupAfter': after,
        'cgroupDelta': {key: after[key]-value for key, value in before.items()},
        'cpuAffinity': sorted(CPUS), 'computeThreads': 4,
        'perProcessAddressSpaceLimitBytes': MEMORY,
        'sampledSummedGroupRssStopThresholdBytes': MEMORY,
        'samplingNote': 'CPU uses own counters by PID/start time, no waited-child double counting; short-lived or exiting processes can be missed. RSS can double-count shared pages and miss peaks. Cgroup deltas are environment-wide, not exclusively attributable to this job.',
    }
    save(prefix.with_suffix('.resources.json'), result)
    return result


def main():
    repair = sys.argv[1:2] == ['--repair-preflight']
    if repair:
        del sys.argv[1]
    host, programs, fixtures, expectations, qualification, old, output = map(
        lambda v: Path(v).resolve(), sys.argv[1:])
    assert 'RISC0_DEV_MODE' not in os.environ
    assert os.environ.get('RISC0_PROVER') == 'ipc'
    assert CPUS <= os.sched_getaffinity(0)
    if not repair:
        output.mkdir()  # Never reuse a proof attempt directory.
    started = time.monotonic()
    deadline = started+3600
    assets = output / 'assets'
    initial_elapsed = 0
    if repair:
        initial = json.loads((output / 'summary.json').read_text())
        assert initial['phases'][0]['status'] == 'completed'
        failed = initial['phases'][1]
        assert failed['phase'] == 'segment-24' and failed['exitCode'] == 1
        assert failed['limitExceeded'] is None
        assert not (assets / 'segment-24-started.json').exists()
        assert not list(assets.glob('segment-*.bin'))
        assert (output / 'segment-24.stderr.log').read_text().strip() == \
            'Error: Os { code: 2, kind: NotFound, message: "No such file or directory" }'
        attempt = json.loads((output / 'attempt.json').read_text())
        initial_elapsed = time.time()-attempt['unixSeconds']
        assert 0 <= initial_elapsed < 3600
        deadline -= initial_elapsed  # Original clock, including repair/build time.
        session = json.loads((assets / 'session.json').read_text())
        for row in session['segments']:
            source = assets / 'segments' / f'segment-{row["index"]}'
            data = source.read_bytes()
            assert hashlib.sha256(data).hexdigest() == row['assetSha256']
            with (assets / 'segments' / f'{row["index"]}.bincode').open('xb') as target:
                target.write(data)
        output = output / 'preflight-repair'
        output.mkdir()  # Exactly one explicit repair; not automatic retry logic.
    save(output / 'attempt.json', {
        'scope': 'ONE_AGGREGATE_BOUNDED_DIAGNOSTIC_ATTEMPT',
        'aggregateSecondsLimit': 3600, 'unixSeconds': time.time(),
        'initialElapsedSecondsIncludingPreflightRepair': initial_elapsed,
        'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'hostSha256': hashlib.sha256(host.read_bytes()).hexdigest(),
        'r0vmSha256': hashlib.sha256(Path(os.environ['RISC0_SERVER_PATH']).read_bytes()).hexdigest(),
        'observedCpuMax': (CGROUP / 'cpu.max').read_text().strip(),
        'observedMemoryMax': (CGROUP / 'memory.max').read_text().strip(),
        'pressureCountersAvailable': {name: (CGROUP / name).is_file()
                                      for name in ('cpu.pressure', 'memory.pressure')},
    })
    common = [str(host), 'phase-diagnostics']
    tasks = [('export', 120, ['export', *map(str, (programs, fixtures, expectations, qualification, assets, old))]),
             ('segment-24', 900, ['segment', str(assets), '24']),
             ('lift-24', 450, ['lift', str(assets), '24']),
             ('segment-25', 900, ['segment', str(assets), '25']),
             ('lift-25', 450, ['lift', str(assets), '25']),
             ('join', 600, ['join', str(assets)]),
             ('verify', 120, ['verify', str(assets)])]
    if repair:
        tasks = tasks[1:]
        # Charge the failed file lookup against the same segment phase budget.
        name, limit, arguments = tasks[0]
        tasks[0] = (name, limit-initial['phases'][1]['seconds'], arguments)
    results = []
    failed = False
    for name, limit, arguments in tasks:
        if failed or time.monotonic() >= deadline:
            results.append({'phase': name, 'status': 'not-attempted'})
            continue
        print(f'START {name} limit={limit}s', flush=True)
        result = phase(common+arguments, limit, output / name, deadline)
        failed = result['exitCode'] != 0 or result['limitExceeded'] is not None
        results.append({'phase': name, 'status': 'failed' if failed else 'completed', **result})
        save(output / 'progress.json' if not (output / 'progress.json').exists()
             else output / f'progress-{name}.json', {'phases': results})
        print(f'END {name} status={results[-1]["status"]} seconds={result["seconds"]:.3f}', flush=True)
    save(output / 'summary.json', {'completedAllPhases': all(r['status'] == 'completed' for r in results),
                                 'seconds': time.monotonic()-started,
                                 'aggregateSecondsIncludingPreflightRepair': initial_elapsed+time.monotonic()-started,
                                 'phases': results})


if __name__ == '__main__':
    main()
