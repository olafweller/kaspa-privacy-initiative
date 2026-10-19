#!/usr/bin/env python3
"""Bounded execution only; no credentials, rental, proving or broadcast."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def group_rss(group):
    total = 0
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = path.read_text().rsplit(') ', 1)[1].split()
            if int(fields[2]) == group:
                total += int(fields[21]) * os.sysconf('SC_PAGE_SIZE')
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            pass
    return total


def main():
    p = argparse.ArgumentParser()
    for name in ['r0vm', 'host', 'program', 'fixtures', 'out']:
        p.add_argument('--' + name, required=True, type=Path)
    a = p.parse_args()
    digest = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
    assert digest(a.r0vm) == '2acdf550f9aca4d05b74072463e4ed307c3824309c754a5cb5f93aa84f3390e6'
    plan_path = Path(__file__).with_name('measurement-plan.json')
    plan = json.loads(plan_path.read_text())
    assert (plan['cycleLimitPerCase'], plan['wallLimitPerCaseSeconds'], plan['wallLimitCampaignSeconds'], plan['threads']) == (160000000, 900, 3600, 4)
    cases = plan['positiveCases']
    cases += json.loads((a.fixtures / 'lifecycle.json').read_text())['additionalExecutionCases']
    a.out.mkdir()
    affinity = sorted(os.sched_getaffinity(0))[:4]
    assert len(affinity) == 4
    env = os.environ.copy()
    env.update(RISC0_PROVER='ipc', RISC0_SERVER_PATH=str(a.r0vm.resolve()),
               RAYON_NUM_THREADS='4', OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4')
    env.pop('RISC0_DEV_MODE', None)
    summary = {'scope': 'NEW_RECOVERY_GUEST_EXECUTION_ONLY_NO_PROOF_RENTAL_OR_BROADCAST',
               'cycleLimitPerCase': 160000000, 'wallLimitPerCaseSeconds': 900,
               'wallLimitCampaignSeconds': 3600, 'affinity': affinity,
               'r0vmSha256': digest(a.r0vm), 'hostSha256': digest(a.host),
               'programSha256': digest(a.program), 'measurementPlanSha256': digest(plan_path), 'cases': [], 'completed': False}
    campaign_start = time.monotonic()
    for name in cases:
        start = time.monotonic()
        peak = 0
        timed_out = False
        with (a.out / (name + '.stdout.log')).open('wb') as out, (a.out / (name + '.stderr.log')).open('wb') as err:
            command = ['taskset', '-c', ','.join(map(str, affinity)), str(a.host),
                       'profile', str(a.program), str(a.fixtures), name, str(a.out / name)]
            child = subprocess.Popen(command, env=env, stdout=out, stderr=err, start_new_session=True)
            while True:
                peak = max(peak, group_rss(child.pid))
                pid, status, usage = os.wait4(child.pid, os.WNOHANG)
                if pid:
                    break
                if not timed_out and (time.monotonic() - start > 900 or time.monotonic() - campaign_start > 3600):
                    os.killpg(child.pid, signal.SIGKILL)
                    timed_out = True
                time.sleep(.1)
        code = os.waitstatus_to_exitcode(status)
        record = {'case': name, 'exitCode': code, 'timeout': timed_out,
                  'wallSeconds': time.monotonic() - start,
                  'peakSampledProcessGroupRssBytes': peak,
                  'wait4MaxRssBytes': usage.ru_maxrss * 1024,
                  'userSeconds': usage.ru_utime, 'systemSeconds': usage.ru_stime}
        summary['cases'].append(record)
        summary['wallSeconds'] = time.monotonic() - campaign_start
        summary['completed'] = code == 0 and len(summary['cases']) == len(cases)
        (a.out / 'campaign.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(json.dumps(record), flush=True)
        if code != 0 or timed_out:
            return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
