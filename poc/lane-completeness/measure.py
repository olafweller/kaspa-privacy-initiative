#!/usr/bin/env python3
"""Measure the local harness and waited prover processes using Linux rusage."""
import json
import pathlib
import resource
import subprocess
import sys
import time

start = time.monotonic()
with open(sys.argv[2], "w") as log:
    result = subprocess.run(sys.argv[3:], stdout=log, stderr=subprocess.STDOUT)
r = resource.getrusage(resource.RUSAGE_CHILDREN)
report = {"command": sys.argv[3:], "exit_code": result.returncode,
          "wall_seconds": time.monotonic()-start, "user_cpu_seconds": r.ru_utime,
          "system_cpu_seconds": r.ru_stime, "max_rss_kib": r.ru_maxrss,
          "rss_scope": "Linux RUSAGE_CHILDREN: largest individual process RSS in waited tree, not summed simultaneous memory",
          "major_page_faults": r.ru_majflt, "minor_page_faults": r.ru_minflt}
pathlib.Path(sys.argv[1]).write_text(json.dumps(report, indent=2)+"\n")
sys.exit(result.returncode)
