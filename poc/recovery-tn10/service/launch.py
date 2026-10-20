"""Bind public trial after deployment; no owner address is baked into the image."""
import base64,json,os
from pathlib import Path
from staged_policy import build,check,sha,validate_trial
from staged_service import App,serve,handler,ThreadingHTTPServer


def materialize(base,volume,raw):
    assert 0<len(raw)<=16384
    trial=validate_trial(json.loads(raw));canonical=raw  # Exact B-approved bytes; no reserialization/hash drift.
    volume.mkdir(parents=True,exist_ok=True)
    config=volume/'public-trial.json'
    if config.exists():assert config.read_bytes()==canonical,'runtime trial cannot change'
    else:
        from staged_policy import write
        write(config,canonical)
    package=volume/'bound-package'
    if package.exists():
        p=check(package);assert p['trialSha256']==sha(config.read_bytes())
    else:build(base/'bin/kpi-recovery-tn10',package,config,base/'guest.program.bin')
    return package


if __name__=='__main__':
    assert any(line.split()[4]=='/workspace' for line in Path('/proc/self/mountinfo').read_text().splitlines())
    raw=base64.b64decode(os.environ['KPI_RECOVERY_PUBLIC_TRIAL_B64'],validate=True)
    volume=Path('/workspace/kpi-recovery-tn10')
    package=materialize(Path('/opt/kpi/recovery-base'),volume,raw)
    check(package,cuda=True)
    app=App(package,volume,os.environ['RUNPOD_POD_ID'],os.environ['KPI_GPU_TOKEN'])
    serve(app,ThreadingHTTPServer(('0.0.0.0',8080),handler(app)))
