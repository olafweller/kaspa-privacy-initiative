"""CPU test harness ONLY; not included in any production image."""
import json
import os
from pathlib import Path
import sys
from http.server import ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'remote-cuda'))
import staged_service
import staged_worker

package,volume,ready,mode=map(str,sys.argv[1:]);package=Path(package)
def execute(package,assets,digest,out,deadline):
    receipt=Path(__file__).resolve().parents[1]/'private-native-proof/gpu-2026-10-18-02/evidence/returned/proofs'/assets.name/'receipt.bin'
    command=[sys.executable,str(Path(__file__).with_name('synthetic_job.py')),str(package/'bin/kpi-private-native-tn10'),str(assets/'target.json'),digest,str(out),str(receipt),mode]
    return staged_worker.execute(package,assets,digest,out,deadline,cuda=False,command=command)
app=staged_service.App(package,Path(volume),'unittest123',os.environ['KPI_SYNTHETIC_TOKEN'],execute=execute)
server=ThreadingHTTPServer(('127.0.0.1',0),staged_service.handler(app))
Path(ready).write_text(json.dumps({'port':server.server_port}))
staged_service.serve(app,server)
