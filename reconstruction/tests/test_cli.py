"""英文 Windows/ASCII 管道下仍可输出中文并正常完成重构。"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ConsoleTests(unittest.TestCase):
    def test_ascii_stdout_full_run(self):
        source=ROOT.parent/'experiments/synthetic'
        cfg=json.loads((source/'config.json').read_text(encoding='utf-8'))
        cfg['input_file']=str(source/'data.csv')
        cfg['row_windows_csv']=str(source/'rows.csv')
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            cfg['output_dir']=str(folder/'results')
            path=folder/'config.json';path.write_text(json.dumps(cfg),encoding='utf-8')
            env=os.environ.copy();env['PYTHONIOENCODING']='ascii'
            result=subprocess.run([sys.executable,str(ROOT/'reconstruct.py'),'run','--config',str(path)],
                                  env=env,capture_output=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stderr.decode('utf-8',errors='replace'))
            self.assertIn('完成',result.stdout.decode('utf-8'))
            self.assertTrue((folder/'results/viewer.html').is_file())
