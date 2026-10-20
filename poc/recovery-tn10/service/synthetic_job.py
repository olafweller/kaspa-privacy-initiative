import sys
from pathlib import Path
sys.path.append(str(next((p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').exists()),Path('/opt/kpi'))/'poc/remote-cuda'))
"""CPU SERVICE TEST ONLY. Copies a retained receipt; never calls a prover.

Not copied into the production image. The real trusted CPU verifier is still
invoked against the independently frozen fixture target in a separate process.
"""
import os
from pathlib import Path
import subprocess
import sys
import time

from common import atomic
from staged_child import identity,gate

binary,target,digest,out,receipt,mode=sys.argv[1:]
out=Path(out)
assert out.is_dir()  # Same parent requirement as the real Rust child.
atomic(out/'supervision.json',identity(os.getpgrp()))
if (out.parents[2]/'state.json').exists():gate(out,digest)
proof=out/'proof';proof.mkdir()
(proof/'candidate-receipt.bin').write_bytes(Path(receipt).read_bytes())
if mode=='fail':raise SystemExit(17)
if mode=='stall':
    subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])
    time.sleep(60)
(proof/'receipt.bin').write_bytes(Path(receipt).read_bytes())
subprocess.run([binary,'verify',target,digest,str(proof/'receipt.bin'),str(out/'cpu')],check=True)
