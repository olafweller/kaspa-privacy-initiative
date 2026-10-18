"""Separate persistent volume and fixed service scope; no provider credential."""
import os
from pathlib import Path
from http.server import ThreadingHTTPServer
from service import App, handler
from lifecycle_package import SCOPE
import lifecycle_worker

if __name__=='__main__':
    assert 'RISC0_DEV_MODE' not in os.environ
    app=App(Path('/opt/kpi/private-native'),Path('/workspace/kpi-private-native'),
            os.environ['RUNPOD_POD_ID'],os.environ['KPI_GPU_TOKEN'],
            execute=lifecycle_worker.execute,scope=SCOPE)
    ThreadingHTTPServer(('0.0.0.0',8080),handler(app)).serve_forever()
