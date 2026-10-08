"""Concrete local installer/unit/forced-route output; never invokes systemd/SSH.
Configuration/PREFUND source hashes supplied externally. No live authorization.
"""
import argparse,hashlib,json,pathlib,sys
import finite_install as f
P=pathlib.Path
def build(role,cfg,pin,source_root,state_root,credential_root=None,credential_pins=None,prefund=None,prefund_seal=None):
 run=cfg['run_id'];m={'schema':'kpi-finite-isolated-standby-install/v1','role':role,'run_id':run,'unit':'kpi-finite-'+role.lower()+'-'+run+'.service','config':state_root+'/config.json','config_sha256':pin,'source_root':source_root,'source_pins':cfg['effective_role_source_pins'][role],'state_root':state_root}
 if role=='C':
  m.update(socket_root=state_root+'/socket',gateway_uid=cfg['gateway_uid'],gateway_gid=cfg['gateway_gid'],prefund_sha256=prefund,prefund_seal_sha256=prefund_seal)
 else:m.update(jail='/srv/kpi-recovery/jail',credentials=credential_root,credential_pins=credential_pins,uid=999,gid=988)
 f.validate(m,cfg,pin);unit=f.render(m,cfg)
 routes={}
 if role=='C':
  for user in ['B','controller']:
   routes[user]='/usr/bin/python3 '+source_root+'/gateway.py --role='+user+' --config '+m['config']+' --config-sha256 '+pin+' --bound-run '+run+' --control-socket '+m['socket_root']+'/control.sock'
 return {'manifest':m,'unit':unit,'forced_commands':routes,'forced_command_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in routes.items()},'installer_sha256':f.sha(P(__file__).parent/'finite_install.py'),'execution_authorized':False,'terminal_execution_authorized':False,'live_ready':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--role',choices=['B','C'],required=True);p.add_argument('--config',required=True);p.add_argument('--config-sha256',required=True);p.add_argument('--source-root',required=True);p.add_argument('--state-root',required=True);p.add_argument('--credential-root');p.add_argument('--credential-pins');p.add_argument('--prefund-sha256');p.add_argument('--prefund-seal-sha256');a=p.parse_args()
 assert f.sha(a.config)==a.config_sha256
 cfg=json.loads(P(a.config).read_bytes());cred=json.loads(P(a.credential_pins).read_bytes()) if a.credential_pins else None
 print(json.dumps(build(a.role,cfg,a.config_sha256,a.source_root,a.state_root,a.credential_root,cred,a.prefund_sha256,a.prefund_seal_sha256),sort_keys=True))
