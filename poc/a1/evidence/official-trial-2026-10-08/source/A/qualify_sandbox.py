import pathlib,json,subprocess,hashlib,os,errno,time,stat
from launcher_common import E,durable
from controller_access import query,load_binding

def inspect_worker(cfg,channel):
 unit=channel['unit']
 props=dict(x.split('=',1) for x in subprocess.check_output(['systemctl','--user','show',unit,'--property=MainPID,MemorySwapMax,StandardOutput,StandardError,LimitCORE'],text=True).splitlines());parent=int(props['MainPID']);pids=[parent]
 for _ in range(4):
  pids+= [int(pid) for p in list(pids) if pathlib.Path(f'/proc/{p}/task/{p}/children').exists() for pid in pathlib.Path(f'/proc/{p}/task/{p}/children').read_text().split() if int(pid) not in pids]
 workers=[pid for pid in pids if pathlib.Path(f'/proc/{pid}/cmdline').exists() and b'/worker/volatile_worker.py' in pathlib.Path(f'/proc/{pid}/cmdline').read_bytes() and b'python3' in pathlib.Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')[0]]
 assert len(workers)==1,'worker namespace unclear';pid=workers[0];mounts=[]
 for line in pathlib.Path(f'/proc/{pid}/mountinfo').read_text().splitlines():
  left,right=line.split(' - ',1);left=left.split();right=right.split();mounts.append({'target':left[4],'options':left[5].split(','),'type':right[0]})
 allowed={'tmpfs','proc','devpts'}
 # bwrap exposes only these individual character devices, not writable disk devices.
 character_devices={'/dev/null','/dev/zero','/dev/full','/dev/random','/dev/urandom','/dev/tty'}
 def nonpersistent(m):
  return m['type'] in allowed or (m['type']=='devtmpfs' and m['target'] in character_devices and stat.S_ISCHR(os.stat(f'/proc/{pid}/root'+m['target']).st_mode))
 all_readonly=all('rw' not in m['options'] or nonpersistent(m) for m in mounts);work=next(m for m in mounts if m['target']=='/work')
 probe=pathlib.Path(f'/proc/{pid}/root/public/.persistent-write-probe')
 try:
  fd=os.open(probe,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd);probe.unlink();raise RuntimeError('persistent artifact mount writable')
 except OSError as e:
  if e.errno!=errno.EROFS:raise
 receipt={'all_persistent_mounts_read_only':all_readonly,'work_is_tmpfs':work['type']=='tmpfs','swap_max_zero':props['MemorySwapMax']=='0','stdout_stderr_null':props['StandardOutput']=='null' and props['StandardError']=='null','core_disabled':props['LimitCORE']=='0','actual_persistent_write_attempt_EROFS':True,'worker_source_sha256':cfg['worker_source_sha256'],'mount_policy_sha256':hashlib.sha256(json.dumps(mounts,sort_keys=True).encode()).hexdigest(),'observed_at':time.time(),'scope':'machine-enforced worker/controller paths, not hardware attestation or hostile-root forensic proof'}
 assert all(receipt[x] for x in ['all_persistent_mounts_read_only','work_is_tmpfs','swap_max_zero','stdout_stderr_null','core_disabled'])
 return receipt

def receipt_path():return E/'sandbox-receipt.json'

def main():
 cfg,channel,_=load_binding(worker=True)
 receipt=inspect_worker(cfg,channel)
 query('sandbox',{'receipt':receipt})
 durable(receipt_path(),receipt)
 print('Read-only mounts, tmpfs, swap/core/stdout restrictions and EROFS qualified; C retained receipt.')

if __name__=='__main__':main()
