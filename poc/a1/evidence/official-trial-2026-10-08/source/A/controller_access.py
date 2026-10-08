"""Bind every continuation helper to the frozen current launcher execution."""
import json,pathlib,subprocess
from launcher_common import E,BASE,read,sha,clean_env

def require(ok,message):
 if not ok:raise ValueError(message)

def validate_config(cfg,planned):
 require(cfg['execution_authorized'] is True,'current live execution not authorized')
 for key in ['run_id','base_instance_id','inventory_sha256','worker_source_sha256','worker_files_sha256']:
  require(cfg[key]==planned[key],'current/planned '+key+' mismatch')
 require(cfg['mode']=='finite-live-native','wrong current execution mode')
 return cfg

def worker_channel(run):
 runtime=pathlib.Path(clean_env()['XDG_RUNTIME_DIR'])/('kpi-live-'+run[-12:])
 require(0<len(str(runtime/'intent.sock').encode('utf-8'))<=107,'AF_UNIX worker intent pathname exceeds 107 UTF-8 bytes')
 return {'runtime':str(runtime),'intent_socket':str(runtime/'intent.sock'),'unit':'kpi-g5-live-volatile-'+run[-12:]+'.service','broker_unit':'kpi-g5-live-intent-'+run[-12:]+'.service'}

def validate_worker(cfg,channel,wc,locator_sha):
 require(channel==worker_channel(cfg['run_id']),'stale/wrong current worker channel')
 require(wc['mode']=='live','wrong worker mode')
 for key in ['run_id','inventory_sha256','worker_source_sha256']:
  require(wc[key]==cfg[key],'worker/current '+key+' mismatch')
 require(wc['S0_locator_sha256']==locator_sha,'worker/current locator mismatch')

def load_binding(worker=False):
 cfg=validate_config(read(E/'live-config.json'),read(E.parent/'planned-live-config.private.json'))
 if not worker:return cfg,None,None
 channel=read(E/'worker-channel.private.json');wc=read(E/'worker-config.private.json')
 validate_worker(cfg,channel,wc,sha(E/'old-S0-locator.json'))
 return cfg,channel,wc

def route(binding):
    r=binding['A_controller_route'];required={'target','key','key_sha256','known_hosts','known_hosts_sha256','host_key_alias','forced_command_sha256','config_sha256','run_id'}
    require(set(r)==required and r['run_id']==binding.get('current_run_id',binding['standby_run_id']),'new fixed controller credential schema')
    require(__import__('re').fullmatch(r'[a-zA-Z0-9_-]+@194\.163\.162\.11',r['target']) and __import__('re').fullmatch('[a-f0-9]{64}',r['forced_command_sha256']),'fixed C target/forced command pin')
    require(r['config_sha256']==binding['C']['config_sha256'],'new route/config binding')
    for k in ['key','known_hosts']:
        p=pathlib.Path(r[k]);require(p.is_absolute() and not p.is_symlink() and p.parent==pathlib.Path(binding['A_credential_root']) and not p.parent.is_symlink() and sha(p)==r[k+'_sha256'],'new local controller credential pin')
    require(pathlib.Path(r['key']).stat().st_mode&0o777==0o600,'controller key permissions')
    require(r['host_key_alias']=='tn10-finite-'+binding['standby_run_id'],'fresh known-host route')
    args=['/usr/bin/ssh','-T','-F','/dev/null','-i',r['key'],'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','LogLevel=ERROR','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+r['known_hosts'],'-o','HostKeyAlias='+r['host_key_alias'],'-o','ForwardAgent=no','-o','ClearAllForwardings=yes',r['target']]
    return args

def transport_for(cfg,binding,op,extra=None):
    q=({'action':'checkpoint'} if op=='finite-checkpoint' else {'action':'independent','run_id':cfg['run_id'],'op':op})
    require(not set(extra or {})&set(q),'controller routing override forbidden');q.update(extra or {})
    return route(binding),json.dumps(q).encode()+b'\n'

def transport(op,extra=None):
    cfg,_,_=load_binding();binding=read(E/'current-runtime-binding.json') if (E/'current-runtime-binding.json').exists() else read(E/'installed-runtime-binding.json')
    return transport_for(cfg,binding,op,extra)

def query(op,extra=None):
 args,raw=transport(op,extra);p=subprocess.run(args,input=raw,capture_output=True,timeout=150)
 if p.returncode:raise ValueError('independent controller rejected '+op)
 reply=json.loads(p.stdout)
 if 'error' in reply:raise ValueError('independent controller rejected '+op)
 return reply
