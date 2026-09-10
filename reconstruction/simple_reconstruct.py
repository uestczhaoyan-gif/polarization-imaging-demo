"""简明入口：读原始数据 → 指定扫描行 → 等分像素 → 奇偶翻转 → 输出。

运行 python reconstruction/simple_reconstruct.py
自己的数据：修改 experiments/tape-frame/config.json，或 --config 自己的.json。
绘图、CSV 和互动网页复用 snake_scan/report.py，日常不需要修改它。
行窗口必须来自测量或明确注明的估计；本脚本不能修复未知变速轨迹。
"""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from snake_scan.core import otsu_threshold
from snake_scan.pipeline import load_measurements, aggregate, positive
from snake_scan.report import write_outputs


def run(config_path):
    config_path = Path(config_path).resolve()
    cfg = json.loads(config_path.read_text(encoding='utf-8-sig'))
    folder = config_path.parent
    for key in ('width_mm', 'line_step_mm'):
        cfg[key] = positive(cfg[key], key)
    cols = positive(cfg['columns'], 'columns', integer=True)
    rows = positive(cfg['rows'], 'rows', integer=True)

    # 1. 全量读数，不删除离群点、不按照片修图。
    raw, points, labels, times, meta = load_measurements(folder/cfg['input_file'], cfg)
    threshold = (otsu_threshold(raw) if cfg.get('threshold_uA') is None
                 else float(cfg['threshold_uA'])*1e-6)
    if not np.isfinite(threshold) or not raw.min() < threshold < raw.max():
        raise ValueError('阈值必须位于电流范围内。')

    # 2. 每条横扫的原始点区间：[起点, 终点)，换行点不参与成像。
    if cfg.get('row_windows_csv'):
        path = folder/cfg['row_windows_csv']
        with path.open(encoding='utf-8-sig', newline='') as f:
            records = list(csv.DictReader(f))
        windows = np.array([[int(r['start_point']), int(r['stop_point_exclusive'])]
                            for r in records])
        directions = [r['direction'] for r in records]
        if len(records) != rows or any(d not in ('forward', 'reverse') for d in directions):
            raise ValueError('窗口行数或方向不正确。')
    else:
        period = positive(cfg['row_period_points'], 'row_period_points')
        start = float(cfg['start_point'])
        fraction = float(cfg.get('scan_fraction', 1))
        if not np.isfinite(start) or start < 0 or not 0 < fraction <= 1:
            raise ValueError('起点或横扫占比无效。')
        starts = start + np.arange(rows)*period
        windows = np.ceil(np.column_stack([starts, starts+period*fraction])).astype(int)
        directions = ['reverse' if r % 2 else 'forward' for r in range(rows)]
    if (windows.min() < 0 or windows.max() > len(raw)
            or np.any(windows[:, 1] <= windows[:, 0])
            or np.any(windows[1:, 0] < windows[:-1, 1])):
        raise ValueError('窗口越界、重叠或长度无效；不自动裁切补点。')

    # 3. 行内按点数等分；要求采样均匀且横扫匀速。
    edges = np.ceil([np.linspace(a, b, cols+1) for a, b in windows]).astype(int)
    reverse = np.array([d == 'reverse' for d in directions])

    # 4. 每像素取中位数；反向行翻转。保留所有点到像素的索引。
    result = aggregate(raw, edges, reverse, threshold)
    counts = np.diff(result['limits'], axis=2)
    cfg['mode'] = 'simple / ' + cfg.get('window_source', 'user supplied')
    meta.update(config=cfg, mode=cfg['mode'], threshold_A=threshold,
                windows=windows.tolist(), directions=directions, window_domain='source_index',
                complete_rows=rows, columns=cols,
                points_per_pixel_min=int(counts.min()), points_per_pixel_max=int(counts.max()),
                points_used=int((result['sample_row'] >= 0).sum()),
                points_excluded=int((result['sample_row'] < 0).sum()),
                notes=['行窗口内按点数等分，要求均匀采样与匀速；未知变速不能由电流唯一恢复。',
                       '坐标从左上角开始，首行向右；实际方向需用实验照片核对。']
                      + cfg.get('notes', []))
    data = dict(raw_current_A=raw, file_point_decimal=points, file_point_original=labels,
                time_s=times, metadata=meta, **result)

    # 5. 输出全原始曲线、双色图、对应表和可离线打开的互动网页。
    output = folder/cfg['output_dir']
    write_outputs(data, output)
    (output/'config_used.json').write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Done: {rows} x {cols}, {len(raw)} original points.')
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path(__file__).resolve().parents[1]/'experiments/tape-frame/config.json')
    run(parser.parse_args().config)
