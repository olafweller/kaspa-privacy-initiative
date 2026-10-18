"""Separate entry point and volume identity for the fixed full-proof attempt."""
import os
from pathlib import Path
from http.server import ThreadingHTTPServer

from service import App, handler
import full_worker

if __name__ == '__main__':
    assert 'RISC0_DEV_MODE' not in os.environ
    app = App(Path('/opt/kpi/full'), Path('/workspace/kpi-full'),
              os.environ['RUNPOD_POD_ID'], os.environ['KPI_GPU_TOKEN'],
              execute=full_worker.execute, scope='FIXED_FULL_CLASSIFIER_ONE_SUCCINCT_RECEIPT')
    ThreadingHTTPServer(('0.0.0.0', 8080), handler(app)).serve_forever()
