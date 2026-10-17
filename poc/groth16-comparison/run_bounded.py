#!/usr/bin/env python3
"""Measure one finite process group; a timeout is never a proof rejection."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

limit, prefix, *command = sys.argv[1:]
limit = int(limit)
assert 0 < limit <= 3600 and command
started = time.monotonic()
expired = threading.Event()
with Path(prefix + '.stdout.log').open('xb') as out, Path(prefix + '.stderr.log').open('xb') as err:
    child = subprocess.Popen(command, stdout=out, stderr=err, start_new_session=True)
    def stop():
        expired.set()
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    def kill():
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    timer = threading.Timer(limit, stop)
    kill_timer = threading.Timer(limit + 15, kill)
    timer.start()
    kill_timer.start()
    _, status, usage = os.wait4(child.pid, 0)
    timer.cancel()
    kill_timer.cancel()
    if expired.is_set():
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
code = os.waitstatus_to_exitcode(status)
Path(prefix + '.resources.json').write_text(json.dumps({
    'command': command, 'secondsBudget': limit, 'budgetExceeded': expired.is_set(),
    'seconds': time.monotonic() - started, 'exitCode': code,
    'userSeconds': usage.ru_utime, 'systemSeconds': usage.ru_stime,
    'maxIndividualProcessRssKiB': usage.ru_maxrss,
}, indent=2) + '\n')
raise SystemExit(124 if expired.is_set() else code)
