"""One root-reviewed read-only finite prefix, no observer or submit API."""
import pathlib,json,hashlib,sys,os,argparse
P=pathlib.Path
encode=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
sha=lambda p:hashlib.sha256(P(p).read_bytes()).hexdigest()
def save(path,value,gid=986):
 raw=encode(value);fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o440)
 with os.fdopen(fd,'wb') as f:os.fchown(f.fileno(),0,gid);os.fchmod(f.fileno(),0o440);f.write(raw);f.flush();os.fsync(f.fileno())
 fd=os.open(P(path).parent,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--ledger-sha256',required=True);a=p.parse_args();root=P(a.root)
 assert os.geteuid()==0 and sha(root/'package-pins.json')==a.ledger_sha256
 ledger=json.loads((root/'package-pins.json').read_bytes())
 for name,h in ledger['files'].items():assert sha(root/name)==h
 cfg=json.loads((root/'config.template.json').read_bytes());assert all(cfg.get(k) is False for k in ['execution_authorized','terminal_execution_authorized','funding_authorized','poweroff_authorized']);assert cfg['finite']['root']==str(root/'state/finite-runs')
 sys.dont_write_bytecode=True;sys.path.insert(0,str(P(cfg['finite']['role_sources']['finite_runtime.py']['path']).parent))
 from finite_runtime import settings,node_binding,config_digest,run_path
 from finite_capture import select_recent_anchor,prefunding,pin_health
 from rpc_local import RPC
 settings(cfg);before=node_binding(cfg);rpc=RPC()
 try:
  pin_health(cfg,rpc);selection=select_recent_anchor(rpc,80);pin_health(cfg,rpc);assert node_binding(cfg)==before
 finally:rpc.close()
 cfg['finite']['origin_hash']=selection['hash'];save(root/'state/origin-selection.json',selection);save(root/'state/config.origin.json',cfg)
 cp=prefunding(cfg);final=dict(cfg,checkpoint=cp);save(root/'state/config.json',final)
 run=run_path(cfg);assert not any((run/n).exists() for n in ['observer-prefunding','events.jsonl','FAULT.json','S1-SEAL.json'])
 assert node_binding(cfg)==before
 print(json.dumps({'run_id':cfg['run_id'],'checkpoint':cp,'config_sha256':sha(root/'state/config.json'),'config_binding_sha256':config_digest(final),'prefund_sha256':sha(run/'PREFUND.json'),'prefund_seal_sha256':sha(run/'PREFUND-SEAL.json'),'prefix_never_observed':True,'authority':False,'funding':False,'submit':False}))
if __name__=='__main__':main()
