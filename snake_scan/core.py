"""将连续电流记录按蛇形扫描映射到二维像素，并保存逐点对应关系。

运行：python reconstruct.py run --config examples/synthetic/config.json

没有时间戳或行同步信号时，自动分行只是估计；本程序不读取照片、不使用
字母模板、不补画轮廓。坐标方向、行周期、起点及换行占时都可显式修改。
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from scipy.ndimage import median_filter
from scipy.signal import correlate
from scipy.optimize import differential_evolution



def read_data(path: Path, index_base='auto'):
    """读取 I(A)、point 两列；保留记录，不根据十进制显示跳号插值。

    仅在十进制不连续、八进制解释连续时自动采用八进制点号。
    行首非数字标题允许跳过；数据开始后的坏行会报错，不能静默丢弃。
    """
    raw = path.read_bytes()
    for encoding in ['utf-8-sig', 'gb18030', 'utf-16']:
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError('无法识别文件编码，请另存为 UTF-8。')
    values, labels = [], []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        fields = line.replace(',', ' ').split()
        try:
            current = float(fields[0])
        except (ValueError, IndexError):
            if not values:
                continue
            raise ValueError(f'第 {line_number} 行不是有效的电流数据。')
        if len(fields) < 2 or not np.isfinite(current):
            raise ValueError(f'第 {line_number} 行缺少点号或电流无效。')
        values.append(current)
        labels.append(fields[1])
    if len(values) < 2:
        raise ValueError('有效数据不足 2 点。')
    decimal = np.asarray([int(label, 10) for label in labels], dtype=np.int64)
    selected_base = 10
    if index_base == 'auto':
        if not np.all(np.diff(decimal) == 1) and all(set(v) <= set('01234567') for v in labels):
            octal = np.asarray([int(label, 8) for label in labels], dtype=np.int64)
            if np.all(np.diff(octal) == 1):
                selected_base = 8
    else:
        selected_base = int(index_base)
    point = np.asarray([int(v, selected_base) for v in labels], dtype=np.int64)
    if not np.all(np.diff(point) == 1):
        raise ValueError('点号存在缺失、重复或非等步长；先核对文件，不可直接等间隔重排。')
    # 内部 source_index 总是文件的第几个数值记录，从 0 开始。
    return np.asarray(values), point, np.asarray(labels), {
        'encoding': encoding, 'point_base': selected_base,
        'sha256': hashlib.sha256(raw).hexdigest(), 'input_points': len(values),
        'source_index_definition': 'zero-based numerical record index; end indices are exclusive',
    }


def otsu_threshold(values):
    """一维 Otsu 阈值；没有照片或形状先验。单位与输入相同。"""
    hist, edges = np.histogram(values, bins=512)
    centers = (edges[:-1] + edges[1:]) / 2
    weight = hist.astype(float) / hist.sum()
    cumulative = np.cumsum(weight)
    moment = np.cumsum(weight * centers)
    score = np.full(len(hist), -np.inf)
    valid = (cumulative > 0) & (cumulative < 1)
    score[valid] = (moment[-1] * cumulative[valid] - moment[valid]) ** 2 / (
        cumulative[valid] * (1 - cumulative[valid]))
    return float(centers[np.argmax(score)])


def fit_row_timing(current, config, threshold):
    """用往返周期和相邻扫描行的一致性估计恒定行周期/相位。

    目标只减少相邻行的差异，不要求结果是 Z。不做逐行自由扭曲。
    这种准则偏好平滑、连续目标；不适合任意棋盘/周期纹理或采集中断。
    """
    if config.get('samples_per_row') is not None and config.get('start_point') is not None:
        period, phase = float(config['samples_per_row']), float(config['start_point'])
        if period <= 0 or not 0 <= phase < len(current):
            raise ValueError('行周期或起始点无效。')
        return period, phase, {'timing_method': 'user supplied constant period and start',
                              'round_trip_peak_samples': None, 'adjacent_row_disagreement': None}
    lo, hi = config['row_period_search']
    fit_start, fit_end = config.get('fit_point_range', [0, len(current)])
    fit_end = min(int(fit_end), len(current))
    fit_start = max(0, int(fit_start))
    if hi <= lo or fit_end - fit_start < 6 * hi:
        raise ValueError('周期搜索范围无效，或拟合区间不足 6 个最长候选行周期。')
    window = int(config.get('alignment_median_window', 31))
    if window < 1 or window % 2 != 1:
        raise ValueError('alignment_median_window 必须为正奇数。')
    binary = (median_filter(current, size=window) >= threshold).astype(float)
    # 自相关只用于报告重复周期。优化范围显式保存在 config 中，便于复查。
    stride = max(1, len(current) // 20000)
    signal = binary[fit_start:fit_end:stride].copy()
    signal -= signal.mean()
    autocorr = correlate(signal, signal, mode='full', method='fft')[len(signal)-1:]
    autocorr /= np.arange(len(signal), 0, -1)
    a, b = max(1, int(2*lo/stride)), min(len(autocorr)-1, int(2*hi/stride))
    repeat = int((np.argmax(autocorr[a:b]) + a) * stride)
    fraction = float(config.get('turnaround_fraction', 0))
    if not 0 <= fraction < .2:
        raise ValueError('turnaround_fraction 应在 [0, 0.2) 内。')
    u = fraction/2 + (1-fraction)*(np.arange(150)+.5)/150
    point = np.arange(len(current))

    def objective(params):
        period, phase = params
        starts = np.arange(phase, len(current)-period, period)
        starts = starts[(starts >= fit_start) & (starts+period <= fit_end)]
        if len(starts) < 4:
            return 1.0
        image = np.interp(starts[:, None]+period*u[None, :], point, binary)
        image[1::2] = image[1::2, ::-1]
        return float(np.abs(np.diff(image, axis=0)).mean())

    if config.get('samples_per_row') is None or config.get('start_point') is None:
        result = differential_evolution(objective, [(lo, hi), (0, hi)],
                                        seed=4, popsize=24, maxiter=110, polish=False)
        period, phase = result.x
    else:
        period = float(config['samples_per_row'])
        phase = float(config['start_point'])
    if not 0 <= phase < len(current) or period <= 0:
        raise ValueError('行周期或起始点无效。')
    return float(period), float(phase), {
        'round_trip_peak_samples': repeat,
        'adjacent_row_disagreement': objective([period, phase]),
        'fit_point_range': [fit_start, fit_end],
        'timing_method': 'constant-period adjacent-row consistency; estimated, not synchronized',
    }


def make_row_windows(n, period, start, fraction):
    """完整周期中间部分作为横扫，换行时间在两端各排除一半。"""
    count = int(np.floor((n-start)/period))
    if count < 1:
        raise ValueError('不足一条完整扫描行。')
    cycle_starts = start + np.arange(count)*period
    return np.column_stack([cycle_starts+period*fraction/2,
                            cycle_starts+period*(1-fraction/2)])
