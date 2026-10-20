"""Build context excludes all actual trial/receive files and all secret files."""
from pathlib import Path
import shutil,sys
from staged_package import base
from staged_policy import ROOT
FILES=('staged_policy.py','staged_child.py','staged_worker.py','staged_service.py','launch.py','run_stage.py','pins.json')

def prepare(out):
    out.mkdir(parents=True);base(out/'base-dist')
    for n in FILES:shutil.copyfile(Path(__file__).with_name(n),out/n)
    for n in ('common.py','worker.py','staged_archive.py'):
        shutil.copyfile(ROOT/'poc/remote-cuda'/n,out/n)
    shutil.copyfile(Path(__file__).with_name('Dockerfile'),out/'Dockerfile')
    assert not any('trial' in p.name or 'receive' in p.name or p.suffix=='.key' or p.name.endswith('.backup') for p in out.rglob('*'))

if __name__=='__main__':prepare(Path(sys.argv[1]))
