from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import json
from tests.test_jmx import fixture


class EntryTests(unittest.TestCase):
    def test_prepare_fixed_cli_readonly(self):
        with tempfile.TemporaryDirectory() as t:
            source=Path(t)/'explicit.jmx';source.write_text(fixture(),encoding='utf-8')
            before=source.read_bytes()
            result=subprocess.run([sys.executable,'-B','-m','scripts.runner','prepare','--source',str(source)],capture_output=True,text=True,encoding='utf-8',env={**__import__('os').environ,'PYTHONIOENCODING':'utf-8'},timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(len(json.loads(result.stdout)['requests']),3)
            self.assertEqual(source.read_bytes(),before)
            self.assertEqual(list(Path(t).iterdir()),[source])

    def test_no_implicit_target(self):
        result=subprocess.run([sys.executable,'-B','-m','scripts.runner','prepare'],capture_output=True,timeout=20)
        self.assertNotEqual(result.returncode,0)


if __name__=='__main__':unittest.main()
