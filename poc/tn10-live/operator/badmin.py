import sys,base64,shlex,json,hashlib
from pathlib import Path
from manage import b,ROOT
BROOT='/var/lib/kpi-cuda-guard/tn10-live-20261019'
ADMIN='/opt/kpi-staged-tn10/live-admin-20261019'
def run(name):
 raw=(ROOT/'admin'/(name+'.py')).read_bytes();assert len(raw)<45000
 code=f'''import pathlib,base64,subprocess,json
p=pathlib.Path({ADMIN!r});p.mkdir(mode=0o700,exist_ok=True);f=p/{name+'.py'!r};d=base64.b64decode({base64.b64encode(raw).decode()!r})
if f.exists():assert f.read_bytes()==d,'changed admin code'
else:f.write_bytes(d);f.chmod(0o600)
r=subprocess.run(['systemd-run','--quiet','--wait','--pipe','--collect','--unit',{'kpi-tn10-live-'+name!r},'--property=EnvironmentFile=/etc/kpi-cuda-guard.env','--property=RuntimeMaxSec=150','--property=UMask=0077','/usr/bin/python3',str(f)],capture_output=True,text=True)
print(r.stdout,end='')
if r.returncode:raise RuntimeError(r.stderr)
'''
 result=b(code);(ROOT/(name+'-b-response.json')).write_text(result);print(result);return result

def public_upload(local,remote):
 data=Path(local).read_bytes();digest=hashlib.sha256(data).hexdigest();tmp=remote+'.upload'
 assert 'wallet' not in remote and not remote.endswith('.key')
 for offset in range(0,len(data),45000):
  chunk=data[offset:offset+45000]
  code=f"import pathlib,base64,os;p=pathlib.Path({tmp!r});p.parent.mkdir(parents=True,exist_ok=True);d=base64.b64decode({base64.b64encode(chunk).decode()!r});f=p.open({'xb' if offset==0 else 'ab'!r});assert f.tell()=={offset};f.write(d);f.flush();os.fsync(f.fileno());f.close()"
  b(code)
 code=f"import pathlib,hashlib,os;p=pathlib.Path({tmp!r});assert hashlib.sha256(p.read_bytes()).hexdigest()=={digest!r};q=pathlib.Path({remote!r});assert not q.exists();os.rename(p,q);q.chmod(0o644);f=os.open(q.parent,os.O_RDONLY);os.fsync(f);os.close(f);print('PUBLIC_ASSET_CHECKED '+str(q))"
 return b(code)
def public_download(remote,local):
 code=f"import pathlib,hashlib,json;p=pathlib.Path({remote!r});d=p.read_bytes();print(json.dumps({{'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()}}))"
 info=json.loads(b(code));data=b''
 for offset in range(0,info['bytes'],524288):
  code=f"import base64;f=open({remote!r},'rb');f.seek({offset});print(base64.b64encode(f.read(524288)).decode())"
  data+=base64.b64decode(b(code).strip())
 assert len(data)==info['bytes'] and hashlib.sha256(data).hexdigest()==info['sha256']
 Path(local).write_bytes(data)
if __name__=='__main__':run(sys.argv[1])
