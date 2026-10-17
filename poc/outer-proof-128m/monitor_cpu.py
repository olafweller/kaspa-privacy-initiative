#!/usr/bin/env python3
"""Read cumulative process-group CPU counters, including before a hard kill.

wait4 on a killed parent may omit a child it never reaped. These /proc samples
retain a separate lower-bound measurement; they are not exact kernel accounting.
Starting observation later does not reset the processes' cumulative counters.
"""
import json
import os
from pathlib import Path
import sys
import time

group = int(sys.argv[1])
prefix = sys.argv[2]
ticks = os.sysconf('SC_CLK_TCK')
started = time.monotonic()
peak_user = peak_system = 0
count = 0
with Path(prefix + '.jsonl').open('x') as log:
    while time.monotonic() - started < 3600:
        user = system = active = 0
        members = []
        for path in sorted((p for p in Path('/proc').iterdir() if p.name.isdigit()),
                           key=lambda p: int(p.name)):
            try:
                fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
                if int(fields[2]) != group:
                    continue
                user += int(fields[11]) + int(fields[13])
                system += int(fields[12]) + int(fields[14])
                active += fields[0] not in ('Z', 'X')
                members.append(int(path.name))
            except (OSError, IndexError, ValueError):
                continue
        peak_user = max(peak_user, user / ticks)
        peak_system = max(peak_system, system / ticks)
        log.write(json.dumps({'unixSeconds': time.time(), 'members': members,
                              'cumulativeUserSeconds': user / ticks,
                              'cumulativeSystemSeconds': system / ticks,
                              'activeMembers': active}) + '\n')
        log.flush()
        count += 1
        if not active:
            break
        time.sleep(1)
with Path(prefix + '.summary.json').open('x') as out:
    out.write(json.dumps({'scope': 'PROC_PROCESS_GROUP_CUMULATIVE_CPU_SAMPLING',
                          'processGroup': group, 'samplingIntervalSeconds': 1,
                          'clockTicksPerSecond': ticks, 'samples': count,
                          'maxSampledCumulativeUserSeconds': peak_user,
                          'maxSampledCumulativeSystemSeconds': peak_system,
                          'note': 'Sampled cumulative counters include observed waited children; disappearing processes can cause gaps. Compare kernel wait4 accounting.'}, indent=2) + '\n')
