"""验证下载后发布快照的完整性、单位和原始采样对应。"""
import hashlib
import json
from pathlib import Path
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


class PublishedResultsTests(unittest.TestCase):
    def test_result_manifest(self):
        folder=ROOT/'results'
        records=(folder/'manifest.sha256').read_text(encoding='utf-8').splitlines()
        self.assertGreater(len(records),20)
        listed=set()
        for line in records:
            expected,name=line.split('  ',1)
            path=folder/name
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),expected,name)
            listed.add(name)
        actual={p.relative_to(folder).as_posix() for sub in ['z_tape','synthetic','dark_80mm_20260909']
                for p in (folder/sub).rglob('*') if p.is_file() and '.mpl-cache' not in p.parts}
        self.assertEqual(listed,actual)

    def test_saved_pixels_and_source_bytes(self):
        with np.load(ROOT/'results/z_tape/reconstruction.npz',allow_pickle=False) as d:
            metadata=json.loads(str(d['metadata_json']))
            original=(ROOT/'examples/z_tape/data/raw_data.txt').read_bytes()
            self.assertEqual(metadata['sha256'],hashlib.sha256(original).hexdigest())
            raw=d['raw_current_A'];limits=d['limits'];image=d['binary']
            self.assertEqual(len(raw),120311)
            for r,c in np.ndindex(image.shape):
                a,b=limits[r,c]
                self.assertEqual(d['median_A'][r,c],np.median(raw[a:b]))
                self.assertEqual(image[r,c],int(np.median(raw[a:b])>=metadata['threshold_A']))
                self.assertTrue(np.all(d['sample_row'][a:b]==r))
                self.assertTrue(np.all(d['sample_col'][a:b]==c))

    def test_dark_data_and_both_mappings(self):
        from snake_scan.core import read_data
        path=ROOT/'examples/dark_80mm_20260909/data/raw_export.xls'
        raw,_,_,info=read_data(path)
        self.assertEqual(info['point_base'],8)
        self.assertEqual(len(raw),20059)
        self.assertEqual(info['sha256'],'079a4905b7261c008347127aea21e42735a4a85c0fd46b373dfa4ef5f352c514')
        for name in ['anchored','uniform']:
            with np.load(ROOT/f'results/dark_80mm_20260909/{name}/reconstruction.npz',allow_pickle=False) as d:
                np.testing.assert_array_equal(d['raw_current_A'],raw)
                self.assertEqual(d['binary'].shape,(40,40))
                for r,c in np.ndindex(40,40):
                    a,b=d['limits'][r,c]
                    self.assertEqual(d['median_A'][r,c],np.median(raw[a:b]))
                    self.assertTrue(np.all(d['sample_row'][a:b]==r))
                    self.assertTrue(np.all(d['sample_col'][a:b]==c))
