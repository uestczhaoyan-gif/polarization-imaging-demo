"""Generate the annotated traces, interactive provenance viewer and verify outputs."""
from pathlib import Path
import json,csv,hashlib
import numpy as np
S=Path(__file__).resolve().parent
ROOT=S.parents[1]
O=S/'comparisons'
records=json.loads((S/'source-manifest.json').read_text(encoding='utf-8'))
for record in records:
    assert hashlib.sha256((S/record['archived_path']).read_bytes()).hexdigest()==record['sha256']
# Per-case annotated original waveform and explicit sample roles.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
for config in sorted(S.glob('*/*/config.json')):
 case=config.parent;cfg=json.loads(config.read_text(encoding='utf-8'));d=np.load(case/'results/reconstruction.npz');raw=d['raw_current_A']*1e6;lim=d['limits'];lo=lim[:,:,0].min(1);hi=lim[:,:,1].max(1)
 turns=np.array(cfg['turnaround_anchor_source_indices']);finish=min(len(raw),round(lo[-1]+turns[-1]-turns[-2]))
 role=np.full(len(raw),'return_or_dwell_estimated',dtype=object);role[:lo[0]]='pre_scan_estimated';role[finish:]='post_motion_tail_estimated'
 for a,b in zip(lo,hi):role[a:b]='forward_used'
 with (case/'results/sample_roles.csv').open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.writer(f);w.writerow(['source_index','role']);w.writerows(enumerate(role))
 fig,ax=plt.subplots(figsize=(13,3.8),layout='constrained');ax.plot(raw,lw=.45,color='#245778')
 for r,(a,b) in enumerate(zip(lo,hi)):
  ax.axvspan(a,b,color='green',alpha=.13,label='Forward scan used' if r==0 else None)
 ax.axvspan(finish,len(raw),color='grey',alpha=.25,label='Estimated stationary tail (not used)')
 ax.set(title=case.name+' | ALL original samples retained',xlabel='Source index (no measured timestamps)',ylabel='Current / uA');ax.legend(fontsize=8)
 fig.savefig(case/'results/00_raw_with_windows.png',dpi=160);plt.close(fig)
 (case/'code').mkdir(exist_ok=True)
 (case/'code/reconstruct.py').write_text('''from pathlib import Path
import sys
CASE=Path(__file__).resolve().parents[1]
ROOT=next(p for p in CASE.parents if (p/'reconstruction/snake_scan').is_dir())
sys.path.insert(0,str(ROOT/'reconstruction'))
from snake_scan.pipeline import reconstruct
from snake_scan.continuous_report import write_outputs
if __name__=='__main__':
    output=ROOT/'local/reconstruction/2026-10-16'/CASE.parent.name/CASE.name
    write_outputs(reconstruct(CASE/'config.json'),output)
    print(output)
''',encoding='utf-8')
 (case/'README.md').write_text(f'''# {case.name}

单向扫描；X范围 {cfg['width_mm']} mm，{cfg['rows']} 行，Y行距1 mm；X设定 {cfg['x_speed_mm_s']} mm/s；NPLC={cfg['nplc']}。原始{len(raw):,}点，成像{cfg['rows']}×{cfg['columns']}像素。

[原始波形及使用区间](results/00_raw_with_windows.png) · [连续电流图](results/02_current_reconstruction.png) · [逐像素查看器](results/viewer.html) · [原始数据](data/current.xls) · [秒表照片](data/stopwatch.jpg)

[配置](config.json) · [分行区间](estimated-row-windows.csv) · [像素到原始点](results/pixel_to_points.csv) · [逐点用途](results/sample_roles.csv) · [单实验复现入口](code/reconstruct.py)

数据无逐点时间戳，图像坐标为计时模型下的名义坐标。尾部、回程、换行数据未参加正向成像，但都保留。逐点用途中的非正扫类别只是估计，不能视为电机实际事件日志。

安装根目录 reconstruction/requirements.txt 后运行本实验 code/reconstruct.py；新输出写入根目录 local/reconstruction/2026-10-16。同批次所有窗口与结果可用上级批次 rebuild.py 重建（会覆盖生成结果）。

[批次分析与结论](../../README.md) · [离线图集](../../index.html)
''',encoding='utf-8')
# Independent geometric check uses C edge at matched reference Y, no extrapolation.
rows=list(csv.DictReader((O/'heldout_C_edge_positions.csv').open(encoding='utf-8-sig')))
ref=[r for r in rows if r['light_percent']=='20'];xx=np.array([float(r['edge_x_before_mm']) for r in ref]);yy=np.array([float(r['source_y_mm']) for r in ref]);checks=[]
for k in ['40','60']:
 a=[r for r in rows if r['light_percent']==k];x0=np.array([float(r['edge_x_before_mm']) for r in a]);x1=np.array([float(r['edge_x_after_mm']) for r in a]);y=np.array([float(r['reference_y_mm']) for r in a]);valid=(y>=yy.min())&(y<=yy.max())
 checks.append(dict(light_percent=int(k),before_mean_abs_mm=float(np.mean(abs(x0[valid]-xx[valid]))),after_mean_abs_mm=float(np.mean(abs(x1[valid]-np.interp(y[valid],yy,xx)))),before_rows=int(valid.sum()),after_rows=int(valid.sum()),note='Same seven source rows before/after; nominal scale; aligned Y interpolated only within measured reference rows; not absolute accuracy.'))
(O/'heldout_geometry_summary.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
f=np.load(O/'registered_currents.npz');valid=f['common_valid'];z=f['current_uA'];reference=f['original_current_uA'][0]
# Conservative interior selection for demonstration, not a statistical confidence bound.
from scipy.ndimage import binary_erosion,maximum_filter,minimum_filter
smooth_region=(maximum_filter(reference,3)-minimum_filter(reference,3))<.1*(np.percentile(reference,95)-np.percentile(reference,5))
interior=binary_erosion(valid,border_value=0)&smooth_region&(reference>80)
np.savetxt(O/'suggested_stable_bright_mask.csv',interior.astype(int),delimiter=',',fmt='%d')
print('Source files verified',len(records),'C edge check',checks,'Stable bright mask',interior.sum())
# Interactive numerical fusion viewer, no color-image intensity fitting.
pro=list(csv.DictReader((O/'common_pixel_source_intervals.csv').open(encoding='utf-8-sig')))
by={}
for row in pro:by.setdefault(f"{row['common_row']},{row['common_col']}",[]).append(row)
values=np.where(np.isfinite(z),z,-1).tolist()
html=r'''<!doctype html><meta charset="utf-8"><title>三次测量：共同像素与原始点</title>
<style>body{font:16px system-ui;max-width:1250px;margin:30px auto;padding:15px;background:#f7f9fb}canvas{width:100%;image-rendering:pixelated;cursor:crosshair}pre{white-space:pre-wrap;background:white;padding:20px}a{color:#125a9c}</style>
<h1>共同像素的数据对应</h1><p>三幅图从左到右为20%、40%、60%；统一电流色标0–1050 μA。点击任一像素，查看三次电流和原始采样区间。灰色为不完整覆盖，不外推补值。</p>
<p>当前值=各相交原始扫描行的“区间电流中位数”按Y覆盖比例加权。Y亚像素配准是模型估计，不是新增位置测量。坐标为20%组的名义坐标。</p>
<canvas id="plot" width="1155" height="140"></canvas><pre id="info">点击像素</pre><p><a href="../README.md">完整结论</a> · <a href="common_pixel_source_intervals.csv">全部原始区间及权重CSV</a> · <a href="common_grid_currents.csv">共同网格三通道电流CSV</a></p>
<script>const values=VALUES, provenance=PROVENANCE;const canvas=document.getElementById('plot'),ctx=canvas.getContext('2d');
function paint(sel){for(let j=0;j<3;j++)for(let r=0;r<20;r++)for(let c=0;c<55;c++){let v=values[j][r][c];ctx.fillStyle=v<0?'#bbb':`hsl(${260-210*Math.min(1,v/1050)} 85% ${20+35*Math.min(1,v/1050)}%)`;ctx.fillRect((j*55+c)*7,r*7,7,7);}if(sel){ctx.strokeStyle='red';ctx.lineWidth=1;for(let j=0;j<3;j++)ctx.strokeRect((j*55+sel[1])*7+.5,sel[0]*7+.5,6,6);}}
canvas.onclick=e=>{let b=canvas.getBoundingClientRect();let c=Math.min(164,Math.floor((e.clientX-b.left)/b.width*165))%55,r=Math.min(19,Math.floor((e.clientY-b.top)/b.height*20));paint([r,c]);let lines=[`共同像素 row=${r}, col=${c}; X=${c+.5}, Y=${r+.5} 名义mm`];for(let j=0;j<3;j++)lines.push(`${[20,40,60][j]}%: ${values[j][r][c]<0?'无完整覆盖':values[j][r][c].toFixed(5)+' μA'}`);lines.push('\n来源区间采用0起始、左闭右开 [start, stop)：');for(let p of provenance[`${r},${c}`]||[])lines.push(`${p.light_percent}%：原始行${p.source_row}，点[${p.start_source_index}, ${p.stop_source_index_exclusive})，${p.sample_count}点；Y权重${Number(p.y_overlap_weight).toFixed(6)}；区间中位数${Number(p.row_interval_median_uA).toFixed(5)} μA`);document.getElementById('info').textContent=lines.join('\n');};paint();</script>'''
html=html.replace('VALUES',json.dumps(values)).replace('PROVENANCE',json.dumps(by))
(O/'fusion-viewer.html').write_text(html,encoding='utf-8')
# Auditable verification: every published pixel and every fusion contribution.
for cfg in S.glob('*/*/config.json'):
 d=np.load(cfg.parent/'results/reconstruction.npz');raw=d['raw_current_A'];lim=d['limits'];med=d['median_A']
 assert np.allclose(np.array([np.median(raw[a:b]) for a,b in lim.reshape(-1,2)]).reshape(med.shape),med,rtol=0,atol=1e-18)
raws={str(k):np.load(S/f'registration/light{k}/results/reconstruction.npz')['raw_current_A']*1e6 for k in [20,40,60]}
for cell,entries in by.items():
 r,c=map(int,cell.split(','))
 for j,k in enumerate(['20','40','60']):
  es=[p for p in entries if p['light_percent']==k]
  if not es:continue
  weights=[float(p['y_overlap_weight']) for p in es];assert abs(sum(weights)-1)<1e-8
  vals=[]
  for p in es:
   value=np.median(raws[k][int(p['start_source_index']):int(p['stop_source_index_exclusive'])]);assert abs(value-float(p['row_interval_median_uA']))<1e-9;vals.append(value)
  assert abs(np.dot(vals,weights)-z[j,r,c])<1e-9
(O/'validation.json').write_text(json.dumps(dict(raw_files_byte_verified=len(records),all_seven_pixel_medians_verified=True,all_fusion_source_medians_and_weights_verified=True,common_valid_pixels=int(valid.sum()),total_grid_pixels=int(valid.size),stable_bright_pixels=int(interior.sum()),scope='Numerical consistency only; not measured positional accuracy.'),indent=2),encoding='utf-8')
