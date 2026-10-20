"""Separate persistent volume and fixed service scope; no provider credential."""
import os
import time
from pathlib import Path
from http.server import ThreadingHTTPServer
from service import App, handler
from recovery_package import SCOPE
import recovery_worker

class RecoveryApp(App):
    def start(self):
        # Reject before consuming the one-attempt marker, not only in the worker.
        assert self.job and self.job.lease['stopUnix']-time.time()>3960, 'proof hour plus effective guard/transfer margin required'
        return super().start()

if __name__=='__main__':
    assert 'RISC0_DEV_MODE' not in os.environ
    app=RecoveryApp(Path('/opt/kpi/recovery'),Path('/workspace/kpi-recovery-six'),
            os.environ['RUNPOD_POD_ID'],os.environ['KPI_GPU_TOKEN'],
            execute=recovery_worker.execute,scope=SCOPE)
    ThreadingHTTPServer(('0.0.0.0',8080),handler(app)).serve_forever()
