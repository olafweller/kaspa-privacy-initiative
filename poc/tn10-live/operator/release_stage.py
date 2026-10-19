import json,pathlib,hashlib,subprocess,sys
from badmin import b,run,BROOT,ROOT
stage=sys.argv[1];cases=['deposit','credit-transfer','exit','reconcile'];index=cases.index(stage);assert index>0
batch=ROOT/(stage+'-batch');t=batch/'target.json';expected=hashlib.sha256(t.read_bytes()).hexdigest();archive=ROOT/(stage+'-public.tar.gz')
subprocess.run(['python3','poc/private-native-tn10/bundle.py',str(batch),expected,str(archive)],check=True)
p=pathlib.Path('poc/tn10-live/evidence')/stage;p.mkdir();(p/'target.json').write_bytes(t.read_bytes());(p/'freeze-report.json').write_bytes((batch/'freeze-report.json').read_bytes());(p/'public.tar.gz').write_bytes(archive.read_bytes())
subprocess.run(['git','add',str(p)],check=True);subprocess.run(['git','commit','-m','Freeze actual TN10 '+stage+' proof input [skip ci]'],check=True);subprocess.run(['git','push','origin','HEAD'],check=True)
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();files={'targets/'+stage+'.json':('target.json',expected),'public/'+stage+'.tar.gz':('public.tar.gz',hashlib.sha256(archive.read_bytes()).hexdigest())}
code=f'''import subprocess,pathlib,hashlib,json,os
root=pathlib.Path({BROOT!r})
files={files!r}
for relative,(source,digest) in files.items():
 path=root/relative;path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.checked-download');assert not path.exists()
 subprocess.run(['curl','-4','--fail','--silent','--show-error','--max-time','60','--retry','2','--retry-all-errors','--retry-delay','1','--output',str(tmp),{'https://raw.githubusercontent.com/olafweller/kaspa-privacy-initiative/'+commit+'/poc/tn10-live/evidence/'+stage+'/'!r}+source],check=True)
 assert hashlib.sha256(tmp.read_bytes()).hexdigest()==digest
 with tmp.open('rb') as f:os.fsync(f.fileno())
 os.rename(tmp,path);path.chmod(0o644);fd=os.open(path.parent,os.O_RDONLY);os.fsync(fd);os.close(fd)
print('INDEPENDENT_B_TARGET_AND_PUBLIC_BUNDLE_CHECKED')
'''
print(b(code))
s=(ROOT/'admin/stage_deposit.py').read_text().replace("stage='deposit'","stage="+repr(stage)).replace("expected='685c2d754a5fa64b09102801a4e7f63a6a78f10722c25025c371ca62c6dec13e'","expected="+repr(expected))
s=s.replace("assert s['state']=='idle' and s['ledger'] is None and not s['results'] and not s['received']", "assert s['state']=='waiting' and s['ledger']['completed']=="+repr(cases[:index])+" and list(s['results'])=="+repr(cases[:index]))
s=s.replace("lease['stopUnix']-time.time()>3960","lease['stopUnix']-time.time()>300 and s['ledger']['deadlineUnix']-time.time()>300")
s=s.replace("atomic(root/'targets-index.json',{stage:{'targetPath':str(target),'targetSha256':expected}})","idx=json.loads((root/'targets-index.json').read_text());assert stage not in idx;idx[stage]={'targetPath':str(target),'targetSha256':expected};atomic(root/'targets-index.json',idx)")
name='stage_'+stage.replace('-','_');(ROOT/'admin'/(name+'.py')).write_text(s);run(name)
