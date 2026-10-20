import sys,json,tempfile,unittest
from pathlib import Path
from launch import materialize
from staged_package import base
from staged_policy import check

class RuntimeBinding(unittest.TestCase):
    def test_public_runtime_binding_is_immutable_and_excludes_secrets(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);b=base(d/'base');raw=Path(__file__).with_name('example-trial.json').read_bytes()
            assert {p.relative_to(b).as_posix() for p in b.rglob('*') if p.is_file()}=={'bin/kpi-recovery-tn10','guest.program.bin'}
            package=materialize(b,d/'volume',raw);p=check(package)
            self.assertEqual(p['cases'],['deposit','credit-transfer','bob-exit','bob-reconcile','alice-exit','alice-reconcile'])
            self.assertEqual(materialize(b,d/'volume',raw),package)
            value=json.loads(raw);value['trial']='aa'*32
            with self.assertRaises(AssertionError):materialize(b,d/'volume',json.dumps(value).encode())
    def test_wallet_secret_fields_are_not_a_runtime_configuration(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);b=base(d/'base');v=json.loads(Path(__file__).with_name('example-trial.json').read_text());v['walletBackup']='not-a-secret-test-string'
            with self.assertRaises(AssertionError):materialize(b,d/'volume',json.dumps(v).encode())

if __name__=='__main__':unittest.main()
