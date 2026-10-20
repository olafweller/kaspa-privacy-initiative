"""Pinned binary/guest only; user receive data is bound privately at runtime."""
import gzip,io,json,tarfile
from pathlib import Path
from staged_policy import ROOT,build,write,sha
from staged_archive import open_archive,read_compressed

EVIDENCE=ROOT/'poc/recovery-tn10/evidence'
FILES={'bin/kpi-recovery-tn10','guest.program.bin'}


def base(out):
    pins=json.loads(Path(__file__).with_name('pins.json').read_text())
    archive=EVIDENCE/'base-package.tar.gz'
    raw=read_compressed(archive,64*1024**2);assert sha(raw)==pins['baseArchiveSha256']
    files={}
    with open_archive(raw,64*1024**2,128*1024**2,len(FILES)) as (tar,members):
        for item in members:
            assert item.name in FILES and item.name not in files and item.isfile() and item.size<=32*1024**2
            files[item.name]=tar.extractfile(item).read()
    assert set(files)==FILES
    out.mkdir(parents=True)
    for n,d in files.items():write(out/n,d)
    (out/'bin/kpi-recovery-tn10').chmod(0o755)
    assert sha(files['bin/kpi-recovery-tn10'])==pins['hostBinarySha256']
    assert sha(files['guest.program.bin'])==pins['programSha256']
    return out


def restore(out,trial=None):
    # Default is an explicitly synthetic public example, never the owner's receive data.
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        b=base(Path(t)/'base')
        return build(b/'bin/kpi-recovery-tn10',out,trial or Path(__file__).with_name('example-trial.json'),b/'guest.program.bin')
