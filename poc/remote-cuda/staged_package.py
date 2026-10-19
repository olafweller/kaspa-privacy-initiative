"""Public executable package identity. It contains no preselected chain input."""
import gzip
import io
import json
from pathlib import Path
import sys
import tarfile
from common import sha
from staged_policy import ROOT, check, write

FILES={'bin/kpi-private-native-tn10','guest.program.bin','trial.json','staged-policy.json'}
EVIDENCE=ROOT/'poc/staged-tn10-service/evidence'


def archive(package,out):
    check(package)
    assert {p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file()}==FILES
    with out.open('xb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as tar:
        for name in sorted(FILES):
            p=package/name;assert not p.is_symlink();data=p.read_bytes()
            entry=tarfile.TarInfo(name);entry.size=len(data);entry.mode=0o755 if name.startswith('bin/') else 0o600
            tar.addfile(entry,io.BytesIO(data))
    return {'sha256':sha(out.read_bytes()),'bytes':out.stat().st_size}


def restore(out):
    identity=json.loads((EVIDENCE/'package-identity.json').read_text())
    raw=(EVIDENCE/'public-package.tar.gz').read_bytes()
    assert sha(raw)==identity['archive']['sha256']
    files={}
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
        for entry in tar:
            assert entry.name in FILES and entry.name not in files and entry.isfile()
            assert 0<=entry.size<=32*1024**2
            files[entry.name]=tar.extractfile(entry).read()
    assert set(files)==FILES
    out.mkdir(parents=True)
    for name,data in files.items():
        assert sha(data)==identity['files'][name]
        write(out/name,data)
    (out/'bin/kpi-private-native-tn10').chmod(0o755)
    return check(out)


if __name__=='__main__':
    assert len(sys.argv)==3 and sys.argv[1]=='restore'
    print(json.dumps(restore(Path(sys.argv[2])),indent=2))
