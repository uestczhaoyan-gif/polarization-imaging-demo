"""静态科学图、可追溯表格和无需联网的双向联动查看器。"""
import csv
import json
import os
from pathlib import Path
import numpy as np


def write_outputs(data, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    meta, raw = data['metadata'], data['raw_current_A']
    cfg = meta['config']
    arrays = {k:v for k,v in data.items() if k not in ('metadata','time_s')}
    if data['time_s'] is not None:
        arrays['time_s'] = data['time_s']
    np.savez_compressed(output/'reconstruction.npz', metadata_json=json.dumps(meta,ensure_ascii=False), **arrays)
    (output/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    rows, cols = data['binary'].shape
    with (output/'pixel_to_points.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['row','col','x_center_nominal_mm','y_scanline_relative_mm','start_source_index',
                         'stop_source_index_exclusive','sample_count','median_current_A','mean_current_A',
                         'std_current_A','high_sample_fraction','binary_0_low_1_high'])
        for r,c in np.ndindex(rows,cols):
            a,b=data['limits'][r,c]
            writer.writerow([r,c,(c+.5)*cfg['width_mm']/cols,r*cfg['line_step_mm'],a,b,b-a,
                             data['median_A'][r,c],data['mean_A'][r,c],data['std_A'][r,c],
                             data['high_fraction'][r,c],data['binary'][r,c]])
    with (output/'sample_to_pixel.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['source_index','file_point_decimal','file_point_original','current_A','time_s','row','col','used_in_image'])
        for i in range(len(raw)):
            writer.writerow([i,data['file_point_decimal'][i],data['file_point_original'][i],raw[i],
                             '' if data['time_s'] is None else data['time_s'][i],
                             data['sample_row'][i],data['sample_col'][i],int(data['sample_row'][i]>=0)])
    np.savetxt(output/'binary_image.csv',data['binary'],fmt='%d',delimiter=',')
    np.savetxt(output/'current_image_uA.csv',data['median_A']*1e6,fmt='%.9g',delimiter=',')
    with (output/'row_windows.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['row','domain','window_start','window_stop','direction','first_used_index','stop_used_index_exclusive'])
        for r,window in enumerate(meta['windows']):
            writer.writerow([r,meta['window_domain'],*window,meta['directions'][r],
                             data['limits'][r,:,0].min(),data['limits'][r,:,1].max()])
    plot_static(data,output)
    export_html(data,output/'viewer.html')
    return output


def plot_static(data,output):
    os.environ.setdefault('MPLCONFIGDIR',str(output/'.mpl-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties,fontManager
    from matplotlib.colors import ListedColormap
    font=Path('C:/Windows/Fonts/msyh.ttc')
    if font.exists():
        fontManager.addfont(str(font))
        plt.rcParams['font.family']=FontProperties(fname=str(font)).get_name()
    plt.rcParams.update({'axes.unicode_minus':False,'axes.spines.top':False,'axes.spines.right':False})
    raw,meta=data['raw_current_A']*1e6,data['metadata']
    cfg=meta['config']
    with plt.rc_context({'path.simplify':False,'agg.path.chunksize':10000}):
        fig,ax=plt.subplots(figsize=(13,4),layout='constrained')
        ax.plot(np.arange(len(raw)),raw,lw=.5,color='#173d65')
        ax.set(xlabel='Source index (point, zero-based)',ylabel='Current / μA',
               title=f'Full original I–point | {len(raw):,} samples | no filtering')
        fig.savefig(output/'01_raw_I_point.png',dpi=180)
        fig.savefig(output/'01_raw_I_point.svg')
        plt.close(fig)
        if data['time_s'] is not None:
            fig,ax=plt.subplots(figsize=(13,4),layout='constrained')
            ax.plot(data['time_s'],raw,lw=.5,color='#173d65')
            ax.set(xlabel='Time / s',ylabel='Current / μA',title=f"Full I–t | {meta['time_source']}")
            fig.savefig(output/'01b_raw_I_time.png',dpi=180)
            plt.close(fig)
    z=data['binary']; nrows,ncols=z.shape
    extent=[0,cfg['width_mm'],nrows*cfg['line_step_mm'],0]
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    axes[0].imshow(z,cmap=ListedColormap(['#173d65','#f0ba57']),vmin=0,vmax=1,
                   extent=extent,interpolation='nearest',aspect='equal')
    axes[0].set(title=f"Two levels: low < {meta['threshold_A']*1e6:g} μA ≤ high")
    im=axes[1].imshow(data['high_fraction'],vmin=0,vmax=1,cmap='viridis',extent=extent,
                      interpolation='nearest',aspect='equal')
    axes[1].set(title='Fraction of high-current samples (mixed ≈ 0.5)')
    fig.colorbar(im,ax=axes[1],label='Fraction, not probability of correctness',shrink=.8)
    for ax in axes:
        ax.set(xlabel='Nominal X / mm',ylabel='Relative row position / mm')
    fig.suptitle(f"{nrows} rows × {ncols} columns | {meta['mode']} | blue = low, yellow = high")
    fig.savefig(output/'02_reconstruction.png',dpi=180)
    fig.savefig(output/'02_reconstruction.svg')
    plt.close(fig)


def export_html(data,path):
    """浏览器载荷用原始数值，不抽稀存储；总览绘制用 min/max 包络。"""
    payload={
        'raw':(data['raw_current_A']*1e6).tolist(),
        'times':None if data['time_s'] is None else data['time_s'].tolist(),
        'median':(data['median_A']*1e6).tolist(),
        'std':(data['std_A']*1e6).tolist(),
        'fraction':data['high_fraction'].tolist(),
        'limits':data['limits'].tolist(), 'meta':data['metadata']}
    encoded=json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    # 数据只放 JSON script，防止用户输入的标题结束 script 标签。
    encoded=encoded.replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    template=Path(__file__).with_name('viewer.html').read_text(encoding='utf-8')
    Path(path).write_text(template.replace('__SCAN_DATA__',encoded),encoding='utf-8')
