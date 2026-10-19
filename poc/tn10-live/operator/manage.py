import base64,json,sys,shlex,hashlib
from pathlib import Path
sys.path.insert(0,'.local/remote-cuda-preparation/b-guard-20261018')
from transport import gateway,b
ROOT=Path('.local/tn10-live-20261019')
REMOTE='/opt/kpi-tn10-live-20261019'
def upload(path,remote):
 import gzip
 data=Path(path).read_bytes();sha=hashlib.sha256(data).hexdigest();packed=gzip.compress(data,mtime=0);tmp=remote+'.upload-gzip'
 assert not str(path).endswith(('.key','.backup'))
 for offset in range(0,len(packed),16000):
  chunk=packed[offset:offset+16000]
  code=f"import pathlib,base64,os;p=pathlib.Path({tmp!r});d=base64.b64decode({base64.b64encode(chunk).decode()!r});f=p.open({'xb' if offset==0 else 'ab'!r});assert f.tell()=={offset};f.write(d);f.flush();os.fsync(f.fileno());f.close()"
  gateway('python3 -c '+shlex.quote(code))
 code=f"import pathlib,gzip,hashlib,os;d=gzip.decompress(pathlib.Path({tmp!r}).read_bytes());assert hashlib.sha256(d).hexdigest()=={sha!r};p=pathlib.Path({remote!r});f=p.open('xb');f.write(d);f.flush();os.fsync(f.fileno());f.close();p.chmod(0o600);fd=os.open(p.parent,os.O_RDONLY);os.fsync(fd);os.close(fd);print('PUBLIC_FILE_STORED '+str(p))"
 return gateway('python3 -c '+shlex.quote(code))
def download(remote,local):
 import gzip
 code=f"import pathlib,gzip,hashlib,json;p=pathlib.Path({remote!r});d=gzip.compress(p.read_bytes(),mtime=0);q=pathlib.Path(str(p)+'.transport.gz');q.write_bytes(d);print(json.dumps({{'size':len(d),'sha256':hashlib.sha256(d).hexdigest()}}))"
 info=json.loads(gateway('python3 -c '+shlex.quote(code)))
 chunks=[]
 for offset in range(0,info['size'],2097152):
  code=f"import pathlib,base64;f=open({remote+'.transport.gz'!r},'rb');f.seek({offset});print(base64.b64encode(f.read(2097152)).decode())"
  chunks.append(base64.b64decode(gateway('python3 -c '+shlex.quote(code)).strip()))
 data=b''.join(chunks);assert len(data)==info['size'] and hashlib.sha256(data).hexdigest()==info['sha256']
 Path(local).write_bytes(gzip.decompress(data))
if __name__=='__main__':
 if sys.argv[1]=='upload':print(upload(sys.argv[2],sys.argv[3]))
 elif sys.argv[1]=='download':download(sys.argv[2],sys.argv[3])
 elif sys.argv[1]=='gateway':print(gateway(sys.argv[2]))
