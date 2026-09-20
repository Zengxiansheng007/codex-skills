import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from scripts.process import command, windows_batch_command, run_jmeter


class ProcessTests(unittest.TestCase):
    def test_unsafe_batch_args_rejected(self):
        for arg in ['x%PATH%','x!','x"','x\n']:
            with self.subTest(arg=arg),self.assertRaises(ValueError):windows_batch_command('jmeter.bat',[arg])

    @unittest.skipUnless(os.name=='nt','Windows batch probe')
    def test_batch_unicode_spaces_metacharacters(self):
        import sys,json
        with tempfile.TemporaryDirectory(prefix='中文 空格 & () ') as t:
            root=Path(t);script=root/'probe.py';bat=root/'probe.cmd'
            script.write_text('import sys,json;print(json.dumps(sys.argv[1:],ensure_ascii=True))',encoding='utf-8')
            bat.write_text('@echo off\n"'+sys.executable+'" "'+str(script)+'" %*\n',encoding='utf-8')
            args=['-n','-t',str(root/'请求 & (1).jmx'),'-l',str(root/'result.jtl')]
            result=subprocess.run(command(bat,args),capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout),args)

    @unittest.skipUnless(os.name=='nt','Windows serial process probe')
    def test_waits_for_end(self):
        import sys,time
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);script=root/'wait.py';bat=root/'wait.cmd'
            script.write_text('import time;time.sleep(.25)',encoding='utf-8')
            bat.write_text('@echo off\n"'+sys.executable+'" "'+str(script)+'"\n',encoding='utf-8')
            paths={k:root/k for k in ['plan','jtl','report','log','console']};paths['plan'].touch()
            started=[];begin=time.monotonic()
            result=run_jmeter(bat,paths,started.append)
            self.assertTrue(result.started);self.assertEqual(result.exit_code,0)
            self.assertEqual(len(started),1);self.assertGreaterEqual(time.monotonic()-begin,.25)


if __name__=='__main__':unittest.main()
