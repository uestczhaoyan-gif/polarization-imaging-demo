import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from snake_scan.pipeline import reconstruct
from snake_scan.report import write_outputs


class ContinuousTests(unittest.TestCase):
    def test_constant_current_needs_no_threshold_and_preserves_exclusions(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            (p/'data.csv').write_text('current_A\n'+'0.000003\n'*12)
            (p/'rows.csv').write_text('start_point,stop_point_exclusive,direction\n1,5,forward\n7,11,reverse\n')
            cfg = dict(input_file='data.csv', mode='index_windows', width_mm=2,
                       line_step_mm=1, columns=2, row_windows_csv='rows.csv', continuous_only=True)
            (p/'config.json').write_text(json.dumps(cfg))
            d = reconstruct(p/'config.json')
            self.assertIsNone(d['metadata']['threshold_A'])
            self.assertNotIn('binary', d)
            self.assertNotIn('high_fraction', d)
            np.testing.assert_array_equal(d['limits'][1], [[9,11],[7,9]])
            np.testing.assert_allclose(d['median_A'], 3e-6)
            self.assertEqual(d['sample_row'][5], -1)
            write_outputs(d, p/'results')
            self.assertFalse((p/'results/binary_image.csv').exists())
            html = (p/'results/viewer.html').read_text(encoding='utf-8')
            self.assertNotIn('id="reset"', html)
            self.assertTrue((p/'results/01_raw_I_point.png').is_file())
