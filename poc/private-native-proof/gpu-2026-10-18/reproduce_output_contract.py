#!/usr/bin/env python3
"""Reproduce PR50's directory-contract fault without invoking any proof command.

The injected executor only performs the same non-recursive mkdir as the pinned
Rust producer/verifier. Any saved placeholder is explicitly synthetic and stays
inside a temporary directory. This is not a proof or a GPU retry.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'poc/remote-cuda'))
import lifecycle_package as package
frozen_runner = Path(__file__).resolve().parent/'evidence/reviewed-lifecycle-runner.py'
spec = importlib.util.spec_from_file_location('reviewed_pr50_runner', frozen_runner)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def reproduce():
    expected_runner = '46b115f457217b677018451e0380e910d339a2931d37f1c1946dfda83994c73c'
    expected_host = '7a08233a896daedf5a437577d2be5ec5a23384d395c576f7b4e7b95866f937bb'
    assert hashlib.sha256(frozen_runner.read_bytes()).hexdigest() == expected_runner
    host = ROOT/'poc/private-native/host/src/bin/proof.rs'
    assert hashlib.sha256(host.read_bytes()).hexdigest() == expected_host
    assert 'fs::create_dir(out)?' in host.read_text()
    rows = []
    for parents in ((), ('proofs',), ('proofs', 'cpu')):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trusted = root/'trusted'
            package.restore(trusted)
            output = root/'output'
            output.mkdir()
            for name in parents:
                (output/name).mkdir()
            seen = []

            def contract_only(case, kind, arguments):
                target = Path(arguments[-1])
                seen.append({'case': case, 'kind': kind, 'parentExists': target.parent.is_dir()})
                target.mkdir()  # std::fs::create_dir, NOT create_dir_all.
                if kind == 'prove':
                    (target/'receipt.bin').write_bytes(b'SYNTHETIC-PATH-CONTRACT-ONLY')
                return 0

            missing = None
            try:
                runner.run(trusted, output, executor=contract_only)
            except FileNotFoundError as error:
                missing = Path(error.filename).parent.relative_to(output).as_posix()
            complete = (output/'pipeline-complete.json').exists()
            if not parents:
                assert missing == 'proofs' and seen[-1]['kind'] == 'prove' and not complete
            elif parents == ('proofs',):
                assert missing == 'cpu' and seen[-1]['kind'] == 'cpu-verify' and not complete
            else:
                assert missing is None and complete and len(seen) == 9
            rows.append({'precreatedParents': list(parents), 'missingParent': missing,
                         'lastCase': seen[-1]['case'], 'lastKind': seen[-1]['kind'],
                         'syntheticPipelineCompleted': complete})
    return {'scope': 'FILESYSTEM_CONTRACT_REPRODUCTION_ONLY_NOT_A_PROOF_OR_GPU_ATTEMPT',
            'reviewedRunnerSha256': expected_runner, 'reviewedRustHostSha256': expected_host,
            'cases': rows, 'realReceiptsProduced': 0, 'proverCommandsExecuted': 0,
            'productionCodeChanged': False, 'providerActions': 0}


if __name__ == '__main__':
    print(json.dumps(reproduce(), indent=2))
