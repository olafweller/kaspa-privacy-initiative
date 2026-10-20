import hashlib,json,os,pwd,shutil,subprocess,sys,time
from pathlib import Path
base=Path('/opt/kpi-remote-cuda')
sys.path.insert(0,str(base))
from common import atomic,sha
root=Path('/var/lib/kpi-cuda-guard/recovery-six-20261020-01')
package=base/'recovery-six-proof-20261020-01'
client=base/'recovery-six-client-20261020-archive-fix/poc/remote-cuda'
unit=Path('/etc/systemd/system/kpi-cuda-recovery-six-20261020-01.service')
assert subprocess.check_output(['hostname','-f'],text=True).strip()=='vmi3641034.contaboserver.net'
assert subprocess.check_output(['timedatectl','show','--value','--property=NTPSynchronized'],text=True).strip()=='yes'
assert shutil.disk_usage('/var/lib/kpi-cuda-guard').free>10*1024**3
assert not root.exists() and not package.exists() and not unit.exists(),'inspect prior setup before any retry'
for name,digest in {'common.py':'5ed5815ae1177f5915852477d270110f3768bd6b61ff5ebd5833b62526e549c3','provider.py':'9e1a65b68da2cff78d3549b6b72c83a6bcbf8a7a540fa7aa1d6faafbebe7380f','watchdog.py':'f057acefdd5d7c54075711228ae5490b5252bb610605837c74b244c1261ed9d0'}.items():
 assert sha((base/name).read_bytes())==digest,name
prefix='https://raw.githubusercontent.com/olafweller/kaspa-privacy-initiative/c4dc4d8126c5497447760828ffc10382609d49a4/'
def public(path):
 return subprocess.check_output(['curl','--fail','--silent','--show-error','--max-time','45',prefix+path],timeout=50)
manifest=json.loads(public('poc/recovery-proof/runmanifest.json'))
for name,digest in manifest['trustedBClientFiles'].items():assert sha((client/name).read_bytes())==digest,name
sys.path.insert(0,str(client))
from recovery_package import check,allowed,CASES,BINS
from recovery_control import extract
account=pwd.getpwnam('kpi-cuda-guard')
root.mkdir(mode=0o750);os.chown(root,account.pw_uid,account.pw_gid)
archive=public('poc/recovery-proof/evidence/public-package.tar.gz')
assert sha(archive)=='42aae900499190386464c36208c0aa2a4b3e6c102e443ff99a714ef8469656c4'
p=root/'trusted-public-package.tar.gz';p.write_bytes(archive);p.chmod(0o640);os.chown(p,0,account.pw_gid)
extract(p,package,sha(archive))
assert {f.relative_to(package).as_posix() for f in package.rglob('*') if f.is_file()}==allowed()
for folder in [package,package/'inputs',package/'bin']:folder.chmod(0o755)
for f in package.rglob('*'):
 if f.is_file():f.chmod(0o755 if f.parent.name=='bin' else 0o644)
policy=check(package)
targets={}
for case in CASES:
 r=subprocess.run([str(package/'bin'/BINS[1]),'check-target',case,str(package/'inputs')],capture_output=True,text=True,timeout=30)
 assert r.returncode==0,r.stderr
 targets[case]=r.stdout.strip()
r=subprocess.run([str(package/'bin'/BINS[1]),'check-native-context'],capture_output=True,text=True,timeout=30)
assert r.returncode==0,r.stderr
native=json.loads(r.stdout)
unit.write_text('''[Unit]
Description=Independent bounded KPI six-receipt GPU guard
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
User=kpi-cuda-guard
Group=kpi-cuda-guard
EnvironmentFile=/etc/kpi-cuda-guard.env
WorkingDirectory=/opt/kpi-remote-cuda
ExecStart=/usr/bin/python3 /opt/kpi-remote-cuda/watchdog.py /var/lib/kpi-cuda-guard/recovery-six-20261020-01/lease.json /var/lib/kpi-cuda-guard/recovery-six-20261020-01/artifacts
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/kpi-cuda-guard/recovery-six-20261020-01
[Install]
WantedBy=multi-user.target
''');unit.chmod(0o644)
subprocess.run(['systemd-analyze','verify',str(unit)],capture_output=True,check=True)
subprocess.run(['systemctl','daemon-reload'],capture_output=True,check=True)
report={'observedUnix':time.time(),'hostname':subprocess.check_output(['hostname','-f'],text=True).strip(),'NTPSynchronized':True,'freeStateBytes':shutil.disk_usage(root).free,'trustedPackage':str(package),'archiveSha256':sha(archive),'workloadSha256':sha((package/'recovery-workload.json').read_bytes()),'client':str(client),'clientFilesSha256':manifest['trustedBClientFiles'],'fixedTargetsChecked':list(targets),'embeddedNativeContext':native,'guardUnit':unit.name,'guardUnitState':subprocess.check_output(['systemctl','show',unit.name,'--property=ActiveState','--property=UnitFileState'],text=True).splitlines(),'providerCalled':False,'proofStarted':False}
atomic(root/'package-qualified.json',report)
print(json.dumps(report,indent=2))
