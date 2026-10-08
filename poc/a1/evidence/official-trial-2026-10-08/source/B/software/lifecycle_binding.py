"""Infrastructure binding only: immutable per-run service configuration."""
import os,re,json,pathlib,hashlib,time,sys
ROOT=pathlib.Path('/work/final-qualification/autonomous-results')
RUN_RE=re.compile(r'[a-z0-9][a-z0-9-]{7,119}\Z')
def identity(env=None):
 explicit=env is not None;env=os.environ if env is None else env
 # %i is captured in the immutable service command line, independently of
 # EnvironmentFile. A replaced env file can never rename an old invocation.
 if explicit:run=env.get('KPI_LIFECYCLE_RUN_ID','') # isolated test injection
 elif pathlib.Path(sys.argv[0]).name in {'recovery_supervisor.py','recover_exit.py'}:
  # These fixed native-recovery children already require --run-id in argparse.
  # Bind to the same immutable argv, never inherit identity from environment.
  if sys.argv.count('--run-id')!=1 or '--bound-run' in sys.argv:raise ValueError('ambiguous recovery child run identity')
  pos=sys.argv.index('--run-id')
  if pos+1>=len(sys.argv) or sys.argv[pos+1].startswith('-'):raise ValueError('missing recovery child run identity')
  run=sys.argv[pos+1]
 elif '--bound-run' in sys.argv:run=sys.argv[sys.argv.index('--bound-run')+1]
 elif pathlib.Path(sys.argv[0]).name=='lifecycle_entry.py' and len(sys.argv)==3:run=sys.argv[2]
 else:raise ValueError('service command line lacks bound run identity')
 inv=env.get('INVOCATION_ID','');pin=env.get('KPI_LIFECYCLE_CONFIG_SHA256','')
 if not RUN_RE.fullmatch(run) or not re.fullmatch(r'[a-f0-9]{32}',inv) or not re.fullmatch(r'[a-f0-9]{64}',pin):raise ValueError('missing or invalid immutable service identity')
 return {'run_id':run,'invocation_id':inv,'config_sha256':pin,'config_path':'/lifecycle/'+run+'/config.json'}
def load_config(env=None):
 i=identity(env);e=os.environ if env is None else env
 if e.get('KPI_LIFECYCLE_RUN_ID')!=i['run_id'] or e.get('KPI_RUN_CONFIG')!=i['config_path']:raise ValueError('environment attempts to redirect bound invocation')
 p=pathlib.Path(i['config_path']);raw=p.read_bytes()
 if p.is_symlink() or hashlib.sha256(raw).hexdigest()!=i['config_sha256']:raise ValueError('immutable service configuration changed')
 c=json.loads(raw)
 if c.get('run_id')!=i['run_id']:raise ValueError('configuration/service run mismatch')
 return c
def record(phase,payload=None,env=None,root=None):
 i=identity(env);directory=(ROOT if root is None else pathlib.Path(root))/i['run_id']/'lifecycle'/i['invocation_id'];directory.mkdir(mode=0o700,parents=True,exist_ok=True)
 v={'schema':'kpi-service-lifecycle/v1',**i,'phase':phase,'at':time.time(),'pid':os.getpid(),'payload':payload or {}};data=json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode();p=directory/(phase+'.json')
 fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 for d in [directory,directory.parent,directory.parent.parent]:
  fd=os.open(d,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 return v
