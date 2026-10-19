import sys,shlex
from manage import gateway,ROOT
receiver="""import sys,pathlib,os,hashlib,json,time
root=pathlib.Path('/var/lib/kpi-cuda-guard/tn10-live-20261019/evidence');root.mkdir(mode=0o750,exist_ok=True)
p=root/'original-native-rpc-and-pages.tar';tmp=p.with_suffix('.partial');assert not p.exists()
h=hashlib.sha256();size=0
with tmp.open('xb') as f:
 while True:
  data=sys.stdin.buffer.read(1048576)
  if not data:break
  f.write(data);h.update(data);size+=len(data)
 f.flush();os.fsync(f.fileno())
os.rename(tmp,p);p.chmod(0o600);fd=os.open(root,os.O_RDONLY);os.fsync(fd);os.close(fd)
print(json.dumps({'path':str(p),'sha256':h.hexdigest(),'bytes':size,'savedUnix':time.time(),'publicRpcAndOriginalPagesOnly':True}))
"""
remote='python3 -c '+shlex.quote(receiver)
code=f'''import pathlib,subprocess,tarfile,hashlib,json,os
root=pathlib.Path('/opt/kpi-tn10-live-20261019')
files=sorted(p for p in root.iterdir() if p.is_file() and ((p.name.endswith('.json') and any(p.name.endswith(x) for x in ['-rpc.json','-accepted.json','-admission.json','-submission-intent.json','-rejected.json','-fresh.json','-failure.json'])) or ('-page-' in p.name and p.name.endswith('.json.gz'))))
assert files and not any(p.suffix in ('.key','.env','.backup') for p in files)
manifest={{p.name:{{'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()}} for p in files}}
m=root/'original-pages-backup-manifest.json';m.write_text(json.dumps(manifest,indent=2));files.append(m)
p=subprocess.Popen(['/usr/local/bin/kpi-b-ssh',{remote!r}],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
class Writer:
 def __init__(self):self.h=hashlib.sha256();self.size=0
 def write(self,data):self.h.update(data);self.size+=len(data);return p.stdin.write(data)
 def flush(self):p.stdin.flush()
 def tell(self):return self.size
writer=Writer()
with tarfile.open(fileobj=writer,mode='w|') as tar:
 for f in files:tar.add(f,arcname=f.name,recursive=False)
p.stdin.close();out=p.stdout.read().decode();err=p.stderr.read().decode();assert p.wait()==0,err
result=json.loads(out);assert result['sha256']==writer.h.hexdigest() and result['bytes']==writer.size
result['sourceFileCount']=len(files);result['sourceManifestSha256']=hashlib.file_digest(m.open('rb'),'sha256').hexdigest();result['directGatewayToBPublicStream']=True
(root/'b-original-native-backup.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
'''
r=gateway('python3 -c '+shlex.quote(code));(ROOT/'b-original-native-backup.json').write_text(r);print(r)
