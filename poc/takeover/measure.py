#!/usr/bin/env python3
"""Measure a finite public-data subprocess. Never record environment variables."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

prefix, *command = sys.argv[1:]
started = time.monotonic()
with Path(prefix + '.stdout.log').open('xb') as out, Path(prefix + '.stderr.log').open('xb') as err:
    child = subprocess.Popen(command, stdout=out, stderr=err)
    _, status, usage = os.wait4(child.pid, 0)
    code = os.waitstatus_to_exitcode(status)
Path(prefix + '.resources.json').write_text(json.dumps({
    'command': command, 'seconds': time.monotonic() - started, 'exitCode': code,
    'userSeconds': usage.ru_utime, 'systemSeconds': usage.ru_stime,
    'maxIndividualProcessRssKiB': usage.ru_maxrss,
}, indent=2) + '\n')
raise SystemExit(code)
