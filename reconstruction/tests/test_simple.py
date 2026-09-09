"""简明入口的手算映射与输入边界检查。"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from simple_reconstruct import run


class SimpleTests(unittest.TestCase):
    def test_forward_reverse_preserve_samples(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'out').mkdir()
            (root/'raw.csv').write_text('current_A\n0\n0\n0.000002\n0.000002\n0.000002\n0.000002\n0\n0\n')
            cfg=dict(input_file='raw.csv',input_format='csv',output_dir='out',
                     width_mm=4,line_step_mm=2,rows=2,columns=2,threshold_uA=1,
                     row_period_points=4,start_point=0)
            path=root/'config.json'; path.write_text(json.dumps(cfg))
            with patch('simple_reconstruct.write_outputs'):
                result=run(path)
            np.testing.assert_array_equal(result['binary'], [[0,1],[0,1]])
            np.testing.assert_array_equal(result['limits'], [[[0,2],[2,4]],[[6,8],[4,6]]])
            self.assertEqual(result['metadata']['points_used'],8)
            for r,c in np.ndindex(2,2):
                a,b=result['limits'][r,c]
                self.assertTrue(np.all(result['sample_row'][a:b]==r))
                self.assertTrue(np.all(result['sample_col'][a:b]==c))

    def test_out_of_bounds_is_not_padded(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'raw.csv').write_text('current_A\n0\n0.000002\n')
            cfg=dict(input_file='raw.csv',input_format='csv',output_dir='out',
                     width_mm=4,line_step_mm=2,rows=2,columns=2,threshold_uA=1,
                     row_period_points=4,start_point=0)
            path=root/'config.json'; path.write_text(json.dumps(cfg))
            with self.assertRaises(ValueError): run(path)
