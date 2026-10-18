"""Own volume identity prevents reusing old proxy-classifier attempt state."""
import os
from pathlib import Path
from http.server import ThreadingHTTPServer
from service import App, handler
from private_package import SCOPE
import private_worker

if __name__ == '__main__':
    assert 'RISC0_DEV_MODE' not in os.environ
    app = App(Path('/opt/kpi/private-note'), Path('/workspace/kpi-private-note'),
              os.environ['RUNPOD_POD_ID'], os.environ['KPI_GPU_TOKEN'],
              execute=private_worker.execute, scope=SCOPE)
    ThreadingHTTPServer(('0.0.0.0', 8080), handler(app)).serve_forever()
