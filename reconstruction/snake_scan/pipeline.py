"""读数、扫描窗口与像素聚合。时间窗仅适用于窗口内匀速横扫。

扩展接口：load_measurements → build_edges → aggregate → report.write_outputs。
像素均对应原始数组中的连续半开区间 [start, stop)，不插值补点。
"""
from pathlib import Path
import csv
import hashlib
import json
import platform
import numpy as np
import scipy
from . import __version__
from .core import read_data, fit_row_timing, make_row_windows, otsu_threshold


def positive(value, name, integer=False):
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise ValueError(f'{name} 必须为正数。') from None
    if not np.isfinite(number) or number <= 0 or (integer and number != int(number)):
        raise ValueError(f'{name} 必须为正' + ('整数。' if integer else '数。'))
    return int(number) if integer else number


def load_measurements(path, config):
    """legacy: I(A),八/十进制点号；csv: current_A[,time_s,point]。

    CSV 点号若存在必须是连续十进制整数；即使没有点号也保留每个记录。
    time_s 必须有限且严格递增，不排序、不填补、不静默删除坏数据。
    """
    path = Path(path)
    fmt = config.get('input_format', 'csv')
    if fmt == 'legacy':
        raw, point, labels, info = read_data(path, config.get('point_base', 'auto'))
        times = None
    elif fmt == 'csv':
        with path.open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or 'current_A' not in reader.fieldnames:
                raise ValueError('CSV 需要 current_A 列，单位为 A。')
            rows = list(reader)
            has_time, has_point = 'time_s' in reader.fieldnames, 'point' in reader.fieldnames
        if not rows:
            raise ValueError('数据为空。')
        try:
            raw = np.array([float(r['current_A']) for r in rows])
            times = np.array([float(r['time_s']) for r in rows]) if has_time else None
            labels = np.array([r['point'] if has_point else str(i) for i, r in enumerate(rows)])
            point = np.array([int(p, 10) for p in labels], dtype=np.int64)
        except (ValueError, TypeError):
            raise ValueError('CSV 中有空值或无效数值；point 必须为十进制整数。') from None
        if not np.all(np.diff(point) == 1):
            raise ValueError('point 缺失、重复或不连续，请先核对丢点。')
        info = {'point_base': 10, 'encoding': 'utf-8-sig'}
    else:
        raise ValueError('input_format 只能为 csv 或 legacy。')
    if not np.all(np.isfinite(raw)):
        raise ValueError('电流含 NaN/Inf，不能静默忽略。')
    if times is not None and (not np.all(np.isfinite(times)) or np.any(np.diff(times) <= 0)):
        raise ValueError('time_s 必须有限且严格递增。')
    if times is not None and config.get('sample_interval_seconds') is not None:
        raise ValueError('已有 time_s，不应同时填写 sample_interval_seconds。')
    time_source = 'measured timestamps' if times is not None else 'unavailable'
    if times is None and config.get('sample_interval_seconds') is not None:
        dt = positive(config['sample_interval_seconds'], 'sample_interval_seconds')
        times = np.arange(len(raw)) * dt
        time_source = 'user supplied constant sampling interval (assumed uniform)'
    info.update(input_points=len(raw), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                time_source=time_source,
                source_index_definition='zero-based numerical record index; stop exclusive')
    return raw, point, labels, times, info


def build_edges(raw, times, config, folder, threshold):
    """返回各行每像素的索引边界、各行方向和可审计元数据。

    estimate/constant 在点号域分箱；index_windows 用实际行索引；
    time_windows 用每行实际时间边界按等时间分箱，支持非等间隔采样。
    """
    cols = positive(config['columns'], 'columns', True)
    mode = config['mode']
    metadata = {'mode': mode}
    if mode in ('estimate', 'constant'):
        if mode == 'estimate':
            if config.get('samples_per_row') is not None or config.get('start_point') is not None:
                raise ValueError('estimate 模式不要填写固定周期/起点；已知它们时用 constant。')
            period, start, fit = fit_row_timing(raw, config, threshold)
            metadata.update(fit)
        else:
            period = positive(config.get('samples_per_row'), 'samples_per_row')
            start = float(config['start_point'])
            if not np.isfinite(start) or start < 0 or start >= len(raw):
                raise ValueError('start_point 必须位于原始记录内。')
        fraction = float(config.get('turnaround_fraction', 0))
        if not np.isfinite(fraction) or not 0 <= fraction < .2:
            raise ValueError('turnaround_fraction 必须在 [0,0.2) 内。')
        windows = make_row_windows(len(raw), period, start, fraction)
        edges = np.ceil(np.array([np.linspace(a, b, cols+1) for a, b in windows])).astype(np.int64)
        reverse = np.arange(len(windows)) % 2 == 1
        if config.get('first_row_reverse', False):
            reverse = ~reverse
        metadata.update(samples_per_row=period, start_point_estimate=start,
                        window_domain='source_index', windows=windows.tolist())
    elif mode in ('index_windows', 'time_windows'):
        window_path = folder / config['row_windows_csv']
        with window_path.open(encoding='utf-8-sig', newline='') as f:
            records = list(csv.DictReader(f))
        fields = ('start_point', 'stop_point_exclusive') if mode == 'index_windows' else ('start_s', 'stop_s')
        try:
            windows = np.array([[float(r[fields[0]]), float(r[fields[1]])] for r in records])
            directions = [r['direction'].strip() for r in records]
        except (KeyError, ValueError, TypeError):
            raise ValueError(f'行窗口 CSV 需要 {fields[0]},{fields[1]},direction 三列。') from None
        if not len(records) or any(d not in ('forward', 'reverse') for d in directions):
            raise ValueError('行窗口不能为空；direction 只能为 forward 或 reverse。')
        if not np.all(np.isfinite(windows)) or np.any(windows[:, 1] <= windows[:, 0]):
            raise ValueError('行窗口必须为有限、正长度区间。')
        if np.any(windows[1:, 0] < windows[:-1, 1]):
            raise ValueError('行窗口重叠或未按采集顺序排列。')
        grid = np.array([np.linspace(a, b, cols+1) for a, b in windows])
        if mode == 'time_windows':
            if times is None:
                raise ValueError('time_windows 需要 time_s 列或实测的固定采样间隔。')
            if windows.min() < times[0] or windows.max() > times[-1]:
                raise ValueError('时间窗超出采集时间覆盖范围；请保留扫描前后记录。')
            edges = np.searchsorted(times, grid, side='left')
            gap_limit = config.get('max_sample_gap_seconds')
            if gap_limit is not None:
                gap_limit = positive(gap_limit, 'max_sample_gap_seconds')
                for a, b in windows:
                    # 连同窗口左右邻近采样检查，避免跨边界的长断点漏检。
                    lo = max(0, int(np.searchsorted(times, a))-1)
                    hi = min(len(times), int(np.searchsorted(times, b))+1)
                    if np.any(np.diff(times[lo:hi]) > gap_limit):
                        raise ValueError('横扫窗口存在超过 max_sample_gap_seconds 的采样间断。')
            metadata['window_domain'] = 'time_s'
        else:
            if np.any(windows != np.floor(windows)):
                raise ValueError('索引窗口必须为整数下标。')
            edges = np.ceil(grid).astype(np.int64)
            metadata['window_domain'] = 'source_index'
        reverse = np.array([d == 'reverse' for d in directions])
        metadata.update(windows=windows.tolist(), row_windows_sha256=hashlib.sha256(window_path.read_bytes()).hexdigest())
    else:
        raise ValueError('mode 必须为 estimate、constant、index_windows 或 time_windows。')
    if np.any(edges < 0) or np.any(edges > len(raw)):
        raise ValueError('行窗口超出原始点范围。')
    metadata['directions'] = ['reverse' if r else 'forward' for r in reverse]
    return edges, reverse, metadata


def aggregate(raw, edges, reverse, threshold, minimum=1):
    """保存每个像素对应的所有原始点；同时保留均值、标准差与混合比例。"""
    rows, cols = len(edges), edges.shape[1]-1
    result = {k: np.empty((rows, cols)) for k in ['median_A', 'mean_A', 'std_A', 'high_fraction']}
    result['limits'] = np.empty((rows, cols, 2), dtype=np.int64)
    result['sample_row'] = np.full(len(raw), -1, dtype=np.int32)
    result['sample_col'] = np.full(len(raw), -1, dtype=np.int32)
    minimum = positive(minimum, 'minimum_samples_per_pixel', True)
    for r in range(rows):
        for k, (a, b) in enumerate(zip(edges[r, :-1], edges[r, 1:])):
            c = cols-1-k if reverse[r] else k
            if b-a < minimum:
                raise ValueError(f'行 {r} 列 {c} 只有 {b-a} 点，小于最低 {minimum} 点；减少 columns 或检查丢点。')
            if np.any(result['sample_row'][a:b] >= 0):
                raise ValueError('行窗口重叠。')
            samples = raw[a:b]
            result['median_A'][r,c] = np.median(samples)
            result['mean_A'][r,c] = samples.mean()
            result['std_A'][r,c] = samples.std()
            result['high_fraction'][r,c] = (samples >= threshold).mean()
            result['limits'][r,c] = a,b
            result['sample_row'][a:b], result['sample_col'][a:b] = r,c
    result['binary'] = (result['median_A'] >= threshold).astype(np.uint8)
    return result


def reconstruct(config_path):
    """主 API：完整结果包含原始采样、索引、时间、配置与版本记录。"""
    config_path = Path(config_path).resolve()
    cfg = json.loads(config_path.read_text(encoding='utf-8-sig'))
    for key in ('input_file', 'mode', 'width_mm', 'line_step_mm', 'columns'):
        if key not in cfg:
            raise ValueError(f'缺少必须参数 {key}。')
    for key in ('width_mm', 'line_step_mm'):
        cfg[key] = positive(cfg[key], key)
    cfg['columns'] = positive(cfg['columns'], 'columns', True)
    if not isinstance(cfg.get('first_row_reverse', False), bool):
        raise ValueError('first_row_reverse 必须是 JSON 布尔值。')
    raw, points, labels, times, meta = load_measurements(config_path.parent/cfg['input_file'], cfg)
    value = cfg.get('threshold_uA')
    threshold = otsu_threshold(raw) if value is None else float(value)*1e-6
    if not np.isfinite(threshold) or not raw.min() < threshold < raw.max():
        raise ValueError('阈值必须位于原始电流最小值与最大值之间。')
    edges, reverse, timing = build_edges(raw, times, cfg, config_path.parent, threshold)
    result = aggregate(raw, edges, reverse, threshold, cfg.get('minimum_samples_per_pixel',1))
    counts = np.diff(result['limits'], axis=2).ravel()
    fraction = result['high_fraction']
    notes = ['坐标为给定宽度和行距下的相对坐标，未校准绝对位置或光斑尺寸。',
             '每行按均匀空间分箱，要求有效横扫窗口内速度恒定；尚不支持编码器轨迹重采样。']
    if cfg['mode'] == 'estimate':
        notes.append('周期/起点来自信号拟合，存在多解；估计图案不能替代同步测量。')
    if cfg['mode'] != 'time_windows':
        notes.append('按点数等分像素，要求有效窗口内采样间隔均匀；有非均匀时间戳请用 time_windows。')
    if cfg['mode'] == 'time_windows' and cfg.get('max_sample_gap_seconds') is None:
        notes.append('未设置采样间断上限；请检查时间间隔分布。')
    if times is None:
        notes.append('无时间轴：积分时间和约数启动等待不会被换算成采样间隔。')
    meta.update(timing)
    meta.update(config=cfg, version=__version__, python=platform.python_version(),
                numpy=np.__version__, scipy=scipy.__version__, threshold_A=threshold,
                complete_rows=result['binary'].shape[0], columns=cfg['columns'],
                points_used=int((result['sample_row']>=0).sum()),
                points_excluded=int((result['sample_row']<0).sum()),
                points_per_pixel_min=int(counts.min()), points_per_pixel_max=int(counts.max()),
                mixed_pixels_fraction_02_to_08=int(((fraction>=.2)&(fraction<=.8)).sum()),
                first_used_source_index=int(result['limits'][:,:,0].min()),
                reported_start_wait_seconds_approx=cfg.get('reported_start_wait_seconds'),
                time_axis_available=times is not None, notes=notes)
    if times is not None and len(times)>1:
        meta['sample_interval_summary_seconds'] = {
            'min':float(np.diff(times).min()), 'median':float(np.median(np.diff(times))),
            'max':float(np.diff(times).max())}
    return dict(raw_current_A=raw, file_point_decimal=points, file_point_original=labels,
                time_s=times, metadata=meta, **result)
