import sys
from pathlib import Path
sys.path.append(str(next((p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').exists()),Path('/opt/kpi'))/'poc/remote-cuda'))
"""CPU test harness ONLY; not included in any production image."""
import json
import os
from pathlib import Path
import sys
from http.server import ThreadingHTTPServer

import staged_service
import staged_worker

package,volume,ready,mode=map(str,sys.argv[1:]);package=Path(package)
def execute(package,assets,digest,out,deadline):
    receipt=staged_service.policy.ROOT/'poc/recovery-proof/gpu-2026-10-20/evidence/results/returned/proofs'/assets.name/'receipt.bin'
    command=[sys.executable,str(Path(__file__).with_name('synthetic_job.py')),str(package/'bin/kpi-recovery-tn10'),str(assets/'target.json'),digest,str(out),str(receipt),mode]
    return staged_worker.execute(package,assets,digest,out,deadline,cuda=False,command=command)
app=staged_service.App(package,Path(volume),'unittest123',os.environ['KPI_SYNTHETIC_TOKEN'],execute=execute)
server=ThreadingHTTPServer(('127.0.0.1',0),staged_service.handler(app))
Path(ready).write_text(json.dumps({'port':server.server_port}))
staged_service.serve(app,server)
