"""CPU-only image smoke: public synthetic binding, no credentials/proof/provider."""
import base64,json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
trial=(root/'example-trial.json').read_bytes()
code='''import base64,json,tempfile
from pathlib import Path
from launch import materialize
from staged_policy import check
from staged_service import App
raw=base64.b64decode(PUBLIC_TRIAL)
with tempfile.TemporaryDirectory() as d:
 p=materialize(Path('/opt/kpi/recovery-base'),Path(d)/'volume',raw)
 policy=check(p,cuda=True)
 app=App(p,Path(d)/'volume','smoketest123','synthetic-cpu-smoke-token-not-credential-0000000000')
 status=app.status();assert status['state']=='unconfigured' and len(policy['cases'])==6
 assert not Path('/opt/kpi/recovery-base/trial.json').exists()
 app.close()
 print(json.dumps({'scope':policy['scope'],'sixCases':policy['cases'],'cpuStartupPassed':True,'ownerReceiveDataInImage':False,'gpuExecution':False,'proofStarted':False,'providerCalled':False}))
'''.replace('PUBLIC_TRIAL',repr(base64.b64encode(trial).decode()))
r=subprocess.run(['docker','run','--rm','--entrypoint','python3',sys.argv[1],'-c',code],capture_output=True,text=True,timeout=120)
assert r.returncode==0,r.stderr
print(r.stdout,end='')
