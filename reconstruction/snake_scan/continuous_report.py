"""Continuous-current outputs. No classification, denoising or image interpolation."""
import csv
import json
from pathlib import Path
import numpy as np


def write_outputs(data, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_hex
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    raw = data['raw_current_A'] * 1e6
    z = data['median_A'] * 1e6
    meta = data['metadata']
    cfg = meta['config']
    lo, hi = cfg.get('color_limits_uA', [float(z.min()), float(z.max())])
    if not lo < hi:
        hi = lo + 1
    meta['color_limits_uA'] = [lo, hi]
    meta['notes'].extend(cfg.get('interpretation_notes', []))
    (output/'metadata.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    arrays = {k: v for k, v in data.items() if k not in ('metadata', 'time_s')}
    np.savez_compressed(output/'reconstruction.npz', **arrays)
    np.savetxt(output/'current_image_uA.csv', z, delimiter=',', fmt='%.10g')
    with (output/'pixel_to_points.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['row', 'col', 'start_source_index', 'stop_source_index_exclusive',
                    'sample_count', 'median_current_A', 'mean_current_A', 'std_current_A'])
        for r, c in np.ndindex(z.shape):
            a, b = data['limits'][r, c]
            w.writerow([r, c, a, b, b-a, data['median_A'][r,c], data['mean_A'][r,c], data['std_A'][r,c]])
    # Keep every original sample and its reversible map, including excluded return/dwell samples.
    with (output/'sample_to_pixel.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['source_index', 'file_point_original', 'current_A', 'row', 'col'])
        w.writerows(zip(range(len(raw)), data['file_point_original'], data['raw_current_A'],
                        data['sample_row'], data['sample_col']))
    with plt.rc_context({'path.simplify': False, 'agg.path.chunksize': 10000}):
        fig, ax = plt.subplots(figsize=(13,4), layout='constrained')
        ax.plot(raw, lw=.45, color='#18466b')
        ax.set(xlabel='Source index (all records, zero-based)', ylabel='Current / uA',
               title=f"{cfg.get('short_title', '')} | Full original I-point | {len(raw):,} samples")
        fig.savefig(output/'01_raw_I_point.png', dpi=180)
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(7,6), layout='constrained')
    im = ax.imshow(z, origin='upper', extent=[0,cfg['width_mm'],z.shape[0]*cfg['line_step_mm'],0],
                   aspect='equal', interpolation='nearest', cmap='viridis', vmin=lo, vmax=hi)
    ax.set(xlabel='Nominal X / mm', ylabel='Nominal scan Y / mm',
           title=f"{cfg.get('short_title', '')}\n{z.shape[0]} rows x {z.shape[1]} columns | estimated row windows")
    fig.colorbar(im, ax=ax, label='Median current / uA')
    fig.savefig(output/'02_current_reconstruction.png', dpi=180)
    fig.savefig(output/'02_current_reconstruction.svg')
    plt.close(fig)
    payload = dict(raw=raw.tolist(), times=None, median=z.tolist(), std=(data['std_A']*1e6).tolist(),
                   limits=data['limits'].tolist(), meta=meta, color_limits=[lo, hi],
                   palette=[to_hex(plt.get_cmap('viridis')(i/255)) for i in range(256)])
    encoded = json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    encoded = encoded.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    template = Path(__file__).with_name('continuous_viewer.html').read_text(encoding='utf-8')
    (output/'viewer.html').write_text(template.replace('__SCAN_DATA__', encoded), encoding='utf-8')
    return output

