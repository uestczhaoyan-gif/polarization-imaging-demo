"""从统一项目根目录运行重构测试，无需先安装本地包。"""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'reconstruction'))
suite=unittest.defaultTestLoader.discover(str(ROOT/'reconstruction/tests'))
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
