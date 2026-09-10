"""验证物理映射和拒绝错误数据，不用“看起来像 Z”作为正确性标准。"""
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from snake_scan.pipeline import load_measurements,build_edges,aggregate,reconstruct
from snake_scan.report import export_html

ROOT=Path(__file__).resolve().parents[1]


class MappingTests(unittest.TestCase):
    def test_direction_and_roundtrip(self):
        raw=np.array([1,1,9,9,9,9,1,1],dtype=float)
        d=aggregate(raw,np.array([[0,2,4],[4,6,8]]),[False,True],5)
        np.testing.assert_array_equal(d['binary'],[[0,1],[0,1]])
        np.testing.assert_array_equal(d['limits'][1],[[6,8],[4,6]])
        for r,c in np.ndindex(2,2):
            a,b=d['limits'][r,c]
            self.assertTrue(np.all(d['sample_row'][a:b]==r))
            self.assertTrue(np.all(d['sample_col'][a:b]==c))

    def test_insufficient_samples_and_overlap(self):
        for edges in [np.array([[0,0,2]]),np.array([[0,2,4],[3,4,5]])]:
            with self.assertRaises(ValueError):aggregate(np.arange(6.),edges,[False,True],2.5)

    def test_irregular_timestamps_and_boundary(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            (p/'rows.csv').write_text('start_s,stop_s,direction\n1,3,forward\n4,6,reverse\n')
            times=np.array([0.,1.,1.2,1.8,2.,2.9,3.,4.,4.8,5.,5.1,5.8,6.,7.])
            raw=np.array([0,1,1,1,9,9,0,9,9,1,1,1,0,0.])
            cfg={'columns':2,'mode':'time_windows','row_windows_csv':'rows.csv'}
            edges,reverse,_=build_edges(raw,times,cfg,p,5.)
            np.testing.assert_array_equal(edges,[[1,4,6],[7,9,12]])
            d=aggregate(raw,edges,reverse,5.)
            np.testing.assert_array_equal(d['binary'],[[0,1],[0,1]])
            self.assertEqual(d['sample_row'][6],-1)  # stop_s 恰好处的点不包含
            self.assertEqual(d['sample_row'][0],-1)  # 启动等待
            cfg['max_sample_gap_seconds']=.1
            with self.assertRaisesRegex(ValueError,'间断'):build_edges(raw,times,cfg,p,5.)

    def test_index_windows_explicit_directions(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            (p/'rows.csv').write_text('start_point,stop_point_exclusive,direction\n1,5,reverse\n6,10,reverse\n')
            cfg={'columns':2,'mode':'index_windows','row_windows_csv':'rows.csv'}
            edges,reverse,_=build_edges(np.arange(11.),None,cfg,p,5.)
            np.testing.assert_array_equal(edges,[[1,3,5],[6,8,10]])
            self.assertTrue(reverse.all())  # 以记录方向为准，不强制奇偶

    def test_invalid_csv(self):
        cases=['point,time_s,current_A\n0,0,1\n2,1,2\n',
               'point,time_s,current_A\n0,0,1\n1,0,2\n',
               'point,current_A\n0,nan\n1,2\n',
               'time_s,current_A\n0,1\n-1,2\n']
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'data.csv'
            for content in cases:
                p.write_text(content)
                with self.assertRaises(ValueError):load_measurements(p,{'input_format':'csv'})

    def test_short_legacy_and_single_constant_row(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'data.txt'
            p.write_text('I(A) point\n'+''.join(f'{i+1} {i:o}\n' for i in range(16)))
            raw,points,labels,times,info=load_measurements(p,{'input_format':'legacy'})
            self.assertEqual(info['point_base'],8)
            cfg={'columns':2,'mode':'constant','samples_per_row':16,'start_point':0}
            edges,reverse,_=build_edges(raw,times,cfg,Path(t),8.5)
            d=aggregate(raw,edges,reverse,8.5)
            np.testing.assert_array_equal(d['binary'],[[0,1]])

    def test_synthetic_example(self):
        d=reconstruct(ROOT.parent/'experiments/synthetic/config.json')
        expected=np.loadtxt(ROOT.parent/'experiments/synthetic/expected_binary.csv',delimiter=',')
        np.testing.assert_array_equal(d['binary'],expected)
        self.assertEqual(d['metadata']['time_source'],'measured timestamps')

    def test_octals_and_original_case(self):
        d=reconstruct(ROOT.parent/'experiments/tape-z/config.json')
        self.assertEqual(d['metadata']['sha256'],'9c72470a2cb5f710918991972a4550bba204f23ee5b4f306a60ed0094f48b9c3')
        np.testing.assert_array_equal(d['file_point_decimal'],np.arange(120311))
        self.assertEqual(d['metadata']['point_base'],8)
        self.assertIsNone(d['time_s'])
        # 用已保存的固定周期复现，不把拟合结果视为真实路径。
        cfg=d['metadata']['config'].copy()
        cfg.update(mode='constant',samples_per_row=d['metadata']['samples_per_row'],start_point=d['metadata']['start_point_estimate'])
        edges,reverse,_=build_edges(d['raw_current_A'],None,cfg,ROOT,12e-6)
        fixed=aggregate(d['raw_current_A'],edges,reverse,12e-6)
        np.testing.assert_array_equal(d['binary'],fixed['binary'])
        for r,c in np.ndindex(d['binary'].shape):
            a,b=d['limits'][r,c]
            self.assertEqual(d['median_A'][r,c],np.median(d['raw_current_A'][a:b]))
            self.assertTrue(np.all(d['sample_row'][a:b]==r))
            self.assertTrue(np.all(d['sample_col'][a:b]==c))
        self.assertEqual(int(np.diff(d['limits'],axis=2).sum()),d['metadata']['points_used'])

    def test_html_payload_escaping(self):
        d=reconstruct(ROOT.parent/'experiments/synthetic/config.json')
        d['metadata']['config']['title']='</script><script>alert(1)</script>'
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'viewer.html';export_html(d,p)
            text=p.read_text(encoding='utf-8')
            self.assertNotIn('</script><script>alert(1)',text)
            payload=text.split('type="application/json">',1)[1].split('</script>',1)[0]
            parsed=json.loads(payload)
            np.testing.assert_array_equal(parsed['raw'],d['raw_current_A']*1e6)


if __name__=='__main__':unittest.main()
