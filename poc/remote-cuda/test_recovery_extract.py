"""B-only archive/actual-CLI regressions. No proving or provider calls."""
import gzip
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from common import sha
import recovery_package as pkg
import recovery_control as control
import staged_archive

class RecoveryArchives(unittest.TestCase):
    def archive(self, rows, kind=None):
        stream=io.BytesIO()
        with tarfile.open(fileobj=stream,mode='w',format=tarfile.PAX_FORMAT) as tar:
            if kind=='gnu':
                header=tarfile.TarInfo('././@LongLink');header.type=tarfile.GNUTYPE_LONGNAME
                metadata=b'x'*(64*1024)+b'\0';header.size=len(metadata)
                tar.addfile(header,io.BytesIO(metadata))
            for name,data in rows:
                item=tarfile.TarInfo(name);item.size=len(data)
                if kind=='pax':item.pax_headers={'comment':'x'*(64*1024)}
                tar.addfile(item,io.BytesIO(data))
        return gzip.compress(stream.getvalue())

    def test_real_cli_from_isolated_pinned_b_client_installation(self):
        import shutil
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);client=root/'b-client';client.mkdir()
            bindings=json.loads((pkg.ROOT/'poc/recovery-proof/runmanifest.json').read_text())['trustedBClientFiles']
            for name,digest in bindings.items():
                source=Path(__file__).parent/name
                self.assertEqual(sha(source.read_bytes()),digest)
                shutil.copy2(source,client/name)
            raw=self.archive([('proofs/deposit/candidate-receipt.bin',b'SYNTHETIC-NOT-A-PROOF'),('stages/log.txt',b'log')])
            source=root/'result.tgz';source.write_bytes(raw)
            env={k:os.environ[k] for k in ('PATH','HOME','LD_LIBRARY_PATH') if k in os.environ}
            r=subprocess.run([sys.executable,str(client/'recovery_control.py'),'extract',str(source),str(root/'out'),sha(raw)],cwd=root,env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(json.loads(r.stdout),{'safeRegularFilesExtracted':2})
            self.assertEqual((root/'out/proofs/deposit/candidate-receipt.bin').read_bytes(),b'SYNTHETIC-NOT-A-PROOF')

    def test_hidden_pax_and_gnu_expansion_stops_before_parser_in_function_and_cli(self):
        rows=[('receipt.bin',b'x')]
        limit=len(gzip.decompress(self.archive(rows)))+1024
        # Execute the actual __main__ branch with only the reviewed helper's
        # expansion budget lowered. Production has no caller-selected limit.
        harness='''import json,runpy,sys
from pathlib import Path
from unittest.mock import patch
script,source,out,digest,limit=sys.argv[1:]
sys.path.insert(0,str(Path(script).parent))
import staged_archive
real=staged_archive.open_archive
staged_archive.open_archive=lambda data,c,e,m:real(data,c,min(e,int(limit)),m)
sys.argv=[script,'extract',source,out,digest]
with patch.object(staged_archive.tarfile,'open',side_effect=AssertionError('tar parser must not run')) as parser:
    try:runpy.run_path(script,run_name='__main__')
    except ValueError as error:
        assert 'expanded archive limit' in str(error)
        parser.assert_not_called()
        assert not Path(out).exists()
        print(json.dumps({'rejectedBeforeTarParser':True}))
        sys.exit(23)
raise AssertionError('oversized metadata was accepted')
'''
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for kind in ('pax','gnu'):
                raw=self.archive(rows,kind);source=root/(kind+'.tgz');source.write_bytes(raw)
                self.assertGreater(len(gzip.decompress(raw)),limit)
                with self.subTest(kind=kind),patch.object(control,'MAX_ARCHIVE_TAR',limit),patch.object(staged_archive.tarfile,'open',side_effect=AssertionError('tar parser must not run')) as parser:
                    with self.assertRaisesRegex(ValueError,'expanded archive limit'):
                        control.extract(source,root/(kind+'-direct'),sha(raw))
                    parser.assert_not_called()
                r=subprocess.run([sys.executable,'-c',harness,str(Path(control.__file__).resolve()),str(source),str(root/(kind+'-cli')),sha(raw),str(limit)],capture_output=True,text=True,timeout=30)
                self.assertEqual(r.returncode,23,r.stderr)
                self.assertTrue(json.loads(r.stdout)['rejectedBeforeTarParser'])

    def test_compressed_read_and_hash_fail_before_decompression(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'large.tgz';source.write_bytes(b'x'*1025)
            with patch.object(control,'MAX_ARCHIVE',1024),patch.object(staged_archive.gzip,'GzipFile',side_effect=AssertionError('gzip must not run')) as decoder:
                with self.assertRaisesRegex(ValueError,'compressed archive limit'):
                    control.extract(source,root/'out','00'*32)
                decoder.assert_not_called()
            raw=self.archive([('one',b'x')]);source.write_bytes(raw)
            with patch.object(staged_archive.gzip,'GzipFile',side_effect=AssertionError('gzip must not run')) as decoder:
                with self.assertRaisesRegex(AssertionError,'archive hash mismatch'):
                    control.extract(source,root/'out','00'*32)
                decoder.assert_not_called()
            self.assertFalse((root/'out').exists())

    def test_visible_file_member_and_path_checks_remain_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'bad.tgz'
            for rows in [[('../outside',b'x')],[('/absolute',b'x')],[('a//b',b'x')],[('duplicate',b'x'),('duplicate',b'y')]]:
                raw=self.archive(rows);source.write_bytes(raw)
                with self.assertRaises(AssertionError):control.extract(source,root/'out',sha(raw))
                self.assertFalse((root/'out').exists())
            stream=io.BytesIO()
            with tarfile.open(fileobj=stream,mode='w') as tar:
                item=tarfile.TarInfo('link');item.type=tarfile.SYMTYPE;item.linkname='../outside';tar.addfile(item)
            raw=gzip.compress(stream.getvalue());source.write_bytes(raw)
            with self.assertRaises(AssertionError):control.extract(source,root/'out',sha(raw))
            for setting,limit,rows,error in [('MAX_MEMBERS',1,[('one',b'x'),('two',b'y')],ValueError),('MAX_FILE',1,[('one',b'xx')],AssertionError),('MAX_CONTENT',1,[('one',b'x'),('two',b'y')],AssertionError)]:
                raw=self.archive(rows);source.write_bytes(raw)
                with self.subTest(limit=setting),patch.object(control,setting,limit):
                    with self.assertRaises(error):control.extract(source,root/'out',sha(raw))
                self.assertFalse((root/'out').exists())


if __name__=='__main__':unittest.main()
