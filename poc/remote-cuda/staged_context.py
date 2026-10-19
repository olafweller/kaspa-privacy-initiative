"""Prepare the exact offline Docker build context; no network or proof calls."""
from pathlib import Path
import shutil
import sys
from staged_package import restore
from staged_policy import ROOT

FILES=('Dockerfile.staged','common.py','worker.py','staged_archive.py','staged_policy.py','staged_child.py','staged_worker.py','staged_service.py')


def prepare(out):
    out.mkdir(parents=True)
    restore(out/'staged-dist')
    for name in FILES:shutil.copyfile(Path(__file__).parent/name,out/name)
    shutil.copyfile(ROOT/'poc/private-native-tn10/run_stage.py',out/'run_stage.py')


if __name__=='__main__':
    assert len(sys.argv)==2
    prepare(Path(sys.argv[1]))
