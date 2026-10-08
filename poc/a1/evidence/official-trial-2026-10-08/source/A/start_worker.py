import pathlib,json,subprocess,time
from launcher_common import E,BASE,NODE,read
from controller_access import load_binding,require

def build_command(cfg=None,runtime=None):
 if cfg is None:cfg,runtime,_=load_binding(worker=True)
 else:
  from controller_access import validate_config,worker_channel
  validate_config(cfg,read(E.parent/'planned-live-config.private.json'));require(runtime==worker_channel(cfg['run_id']),'stale/wrong current worker channel')
 instance=read(E/'run-location.private.json')
 approved=read(E.parent/'live-candidate-run-location.private.json')
 require(instance==approved and instance['run_id']==cfg['run_id'],'wrong current instance location')
 bundle=pathlib.Path(instance['path'])
 require(bundle.name==cfg['base_instance_id'],'wrong current base instance')
 args=['systemd-run','--user','--quiet','--unit='+runtime['unit'],'--property=MemoryMax=1G','--property=MemorySwapMax=0','--property=CPUQuota=150%','--property=Nice=10','--property=LimitCORE=0','--property=StandardOutput=null','--property=StandardError=null','--property=NoNewPrivileges=yes','--property=IPAddressDeny=any','--property=IPAddressAllow=localhost','bwrap','--unshare-all','--share-net','--new-session','--die-with-parent','--clearenv','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--tmpfs','/work']
 node=NODE;pin=json.loads((BASE/'boundary-final/node-runtime-pin.json').read_text());import hashlib
 assert hashlib.sha256(node.read_bytes()).hexdigest()==pin['sha256']
 bindings=[(str(node),'/software/node'),('/usr','/usr'),('/lib','/lib'),('/lib64','/lib64'),('/bin','/bin'),('/etc/passwd','/etc/passwd'),('/etc/nsswitch.conf','/etc/nsswitch.conf'),('/etc/hosts','/etc/hosts'),('/etc/resolv.conf','/etc/resolv.conf'),(str(bundle/'public'),'/public'),(str(bundle/'bundle/claim-secret.bin'),'/backup/claim-secret.bin'),(str(E/'worker-config.private.json'),'/worker/config.json'),(runtime['intent_socket'],'/intent.sock'),(str(BASE.parent/'worktrees/a1-poc/poc/a1/target/release/kpi-poc-a1'),'/software/native'),(str(BASE.parent/'worktrees/a1-poc/poc/a1/target/release/a1_reference'),'/software/reference'),(str(BASE.parent/'sdk/kaspa-wasm32-sdk/nodejs/kaspa'),'/sdk')]
 for name in cfg['worker_files_sha256']:bindings.append((str(BASE/'boundary-final'/name),'/worker/'+name))
 for name in ['a1_check.py','a1_recovery.py','a1_recovery_rehearsal.py']:bindings.append((str(BASE.parent/'worktrees/a1-poc/scripts'/name),'/software/'+name))
 for origin,target in bindings:args+=['--ro-bind',origin,target]
 args+=['--bind',runtime['runtime'],'/channel','--setenv','HOME','/nonexistent','--setenv','PATH','/usr/bin:/bin','--setenv','PYTHONPATH','/software','--setenv','RAYON_NUM_THREADS','2','--setenv','PYTHONDONTWRITEBYTECODE','1','--chdir','/work','/usr/bin/python3','/worker/volatile_worker.py']
 return args,runtime

def main():
 args,runtime=build_command()
 for _ in range(30):
  if pathlib.Path(runtime['intent_socket']).exists():break
  time.sleep(.1)
 require(pathlib.Path(runtime['intent_socket']).exists(),'current intent broker socket absent')
 subprocess.run(args,check=True,capture_output=True)
 print('Pinned native continuation worker/SDK adapter started in RAM-only namespace; authorized one-shot live backend; no durable accepted S1 state.')

if __name__=='__main__':main()
