FROM ghcr.io/olafweller/kaspa-privacy-initiative/cuda-qualification@sha256:fb6af438a2f4735b878d07ea5ddfd709c4bd7ecf4b4327df4314286076eb51a6
COPY base-dist /opt/kpi/recovery-base
COPY common.py worker.py staged_archive.py staged_policy.py staged_child.py staged_worker.py staged_service.py launch.py run_stage.py pins.json /opt/kpi/app/
RUN python3 -c "import json,os;from pathlib import Path;from common import sha;p=json.loads(Path('pins.json').read_text());assert sha(Path('/opt/kpi/recovery-base/bin/kpi-recovery-tn10').read_bytes())==p['hostBinarySha256'];assert sha(Path(os.environ['RISC0_SERVER_PATH']).read_bytes())=='4447bbfa89b450611deda80825387d48cce6d23b428310ac45662f5c65f1cbcb'"
CMD ["python3", "launch.py"]
