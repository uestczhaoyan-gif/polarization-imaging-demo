"""Rebuild the five cases. Anchors are estimates, never encoder measurements.

python experiments/2026-09-28/rebuild.py
Core: anchors -> scan-only windows -> raw-sample median -> continuous color.
"""
from pathlib import Path
import csv
import hashlib
import json
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]/'reconstruction'))
from snake_scan.pipeline import reconstruct
from snake_scan.continuous_report import write_outputs


def interpolate_extrapolate(x, xp, fp):
    y = np.interp(x, xp, fp)
    for mask, a, b in [(x < xp[0], 0, 1), (x > xp[-1], -2, -1)]:
        y[mask] = fp[a] + (x[mask]-xp[a])*(fp[b]-fp[a])/(xp[b]-xp[a])
    return y


def prepare_windows(case, cfg):
    n = cfg['rows']
    period = cfg['reported_motion_seconds']/n
    scan = cfg['width_mm']/cfg['x_speed_mm_s']
    single = cfg['unidirectional']
    overhead = period - scan*(2 if single else 1)
    if overhead <= 0:
        raise ValueError('Reported duration is shorter than nominal travel.')
    anchors = np.asarray(cfg['turnaround_anchor_source_indices'])
    # Far-edge plateau center represents a boundary inside a dwell interval.
    # Split total overhead equally across X return/Y transitions in single mode.
    anchor_times = (np.arange(len(anchors))*period + scan + overhead/6 if single
                    else (2*np.arange(len(anchors))+1)*period - overhead/2)
    starts = np.arange(n)*period
    stops = starts+scan
    phase = cfg.get('phase_offset_mm', 0)/cfg['x_speed_mm_s']
    starts, stops = starts+phase, stops+phase
    windows = interpolate_extrapolate(np.stack([starts, stops]), anchor_times, anchors)
    windows = np.rint(windows).astype(int)
    if windows.min() < 0:
        raise ValueError('Estimated first scan precedes data. Review phase/anchors.')
    with (case/'estimated-row-windows.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['start_point','stop_point_exclusive','direction'])
        for r, (a,b) in enumerate(windows.T):
            w.writerow([a,b,'reverse' if not single and r%2 else 'forward'])


def main():
    for config in sorted(HERE.glob('*/config.json')):
        cfg = json.loads(config.read_text(encoding='utf-8'))
        prepare_windows(config.parent, cfg)
        data = reconstruct(config)
        write_outputs(data, config.parent/'results')
        print(config.parent.name, data['median_A'].shape, 'points/pixel',
              data['metadata']['points_per_pixel_min'], data['metadata']['points_per_pixel_max'])
    files = sorted(p for p in HERE.rglob('*') if p.is_file() and p.name != 'manifest.sha256'
                   and '__pycache__' not in p.parts and '.mpl-cache' not in p.parts)
    (HERE/'manifest.sha256').write_text(''.join(
        hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(HERE).as_posix()+'\n'
        for p in files), encoding='utf-8')


if __name__ == '__main__':
    main()
