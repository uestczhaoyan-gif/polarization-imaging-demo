"""本次旧格式数据的探索性分行；不是通用自动识别器。

20 个重复高平台被假设为20次往返的同一相位，线性插值得到40行。
平台不等于到位信号；异常周期内的位置失真仍然保留。
"""
import csv
import json
from pathlib import Path
import sys
import numpy as np
from scipy.ndimage import label, median_filter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from snake_scan.core import read_data


def prepare():
    raw, _, _, _ = read_data(HERE/'data/raw_export.xls')
    groups, count = label(median_filter(raw*1e6, size=9) > 64)
    centers = [float(np.flatnonzero(groups == k).mean()) for k in range(1, count+1)
               if np.count_nonzero(groups == k) > 20]
    if len(centers) != 20:
        raise ValueError('本例应识别20个平台；数据改变后需重新检查，不强制凑行数。')
    centers = np.array(centers)
    intervals = np.diff(centers)
    # 平台中心作为奇数行边界的相位假设；首尾用相邻周期外推。
    phase = np.arange(20)*2+1
    support = np.r_[centers[0]-intervals[0], centers, centers[-1]+intervals[-1]]
    support_phase = np.r_[-1, phase, 41]
    positions = np.interp(np.arange(41), support_phase, support)
    windows = np.ceil(np.column_stack([
        positions[:-1]+.03*np.diff(positions),
        positions[1:]-.03*np.diff(positions)])).astype(int)
    with (HERE/'estimated_windows.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['start_point', 'stop_point_exclusive', 'direction'])
        for r, (a,b) in enumerate(windows):
            w.writerow([a,b,'reverse' if r % 2 else 'forward'])
    with (HERE/'waveform_anchors.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['anchor_number_1based','center_source_index','previous_interval_points'])
        for k,c in enumerate(centers): w.writerow([k+1,c,'' if k==0 else intervals[k-1]])
    cfg = json.loads((HERE/'simple.json').read_text(encoding='utf-8'))
    cfg.pop('row_windows_csv')
    cfg.update(output_dir='../../outputs/dark_80mm_20260909/uniform',
               start_point=int(windows[0,0]), row_period_points=float(np.median(intervals)/2),
               scan_fraction=.94, window_source='constant-period comparison only',
               title='80 mm 暗场实验：固定周期对照，不能校正异常运动')
    (HERE/'uniform.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Anchors:',len(centers),'interval median:',np.median(intervals),'minimum:',intervals.min())


if __name__ == '__main__':
    prepare()
