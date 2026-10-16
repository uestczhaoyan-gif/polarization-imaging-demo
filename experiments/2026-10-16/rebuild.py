"""Rebuild the seven cases from archived inputs. Overwrites generated results only."""
from pathlib import Path
import sys,json,shutil,csv,hashlib
import numpy as np
from scipy.signal import find_peaks,peak_widths
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'reconstruction'))
from snake_scan.pipeline import reconstruct
from snake_scan.continuous_report import write_outputs
OUT=ROOT/'experiments/2026-10-16';OUT.mkdir(exist_ok=True)
# Original input files are already archived below each case/data directory.
specs=[('acquisition/A-v10-nplc0p1','V10N0.1',10,.1,5,85,13,113.68),('acquisition/B-v10-nplc0p01','V10N0.01',10,.01,5,85,14.62,111.02),('acquisition/C-v10-nplc1','V10N1',10,1,5,85,15.42,109.92),('acquisition/D-v1-nplc0p1','V1N0.1',1,.1,5,85,12.48,879.02),('registration/light20','20%N0.1',1,.1,20,55,11.46,2359.43),('registration/light40','40%',1,.1,20,55,41.76,2373.14),('registration/light60','60%',1,.1,20,55,14.45,2324.26)]
for name,stem,v,nplc,rows,width,wait,motion in specs:
 case=OUT/name;(case/'data').mkdir(parents=True,exist_ok=True)
 lines=(case/'data/current.xls').read_text(encoding='gb18030').splitlines()[1:]
 a=np.array([float(line.split()[0]) for line in lines if line.strip()])*1e6
 if rows==5:
  pk,_=find_peaks(a,height=260,prominence=150,distance=len(a)//70);assert len(pk)==20
  _,_,l,h=peak_widths(a,pk,rel_height=.5)
  # Turnaround lies between the two occurrences of the right-hand bright gap.
  centers=(l+h)/2;turns=(centers[1::4]+centers[2::4])/2
 else:
  mask=a>np.quantile(a,.99)*.94;s=np.flatnonzero(np.diff(mask.astype(int),prepend=0)==1);e=np.flatnonzero(np.diff(mask.astype(int),append=0)==-1)+1
  selected=[(x,y) for x,y in zip(s,e) if y-x>1000];assert len(selected)==20
  turns=np.array([(x+y)/2 for x,y in selected])
 periods=np.interp(np.arange(rows),np.arange(rows-1)+.5,np.diff(turns))
 # Stopwatch duration gives approximate cycle duration, not a true per-point clock.
 cycle_seconds=motion/rows
 if rows==5:
  # Stopwatch stopping can include stationary tail. Do not shrink scan windows
  # to that duration: use commanded travel plus assumed Y=X speed and 3x0.3s dwell.
  # This is a model, not a measured acquisition clock. Marker-normalized analysis
  # below does not depend on this absolute mm scale.
  cycle_seconds=2*width/v+1/v+.9
 rate=periods/cycle_seconds
 ends=np.rint(turns).astype(int);starts=np.rint(turns-width/v*rate).astype(int)
 assert starts.min()>=0 and ends.max()<len(a)
 with (case/'estimated-row-windows.csv').open('w',newline='',encoding='utf-8') as f:
  w=csv.writer(f);w.writerow(['start_point','stop_point_exclusive','direction']);w.writerows((s,e,'forward') for s,e in zip(starts,ends))
 cols=int(width) if stem!='V10N1' else 85
 # Low-rate group can have empty 1-mm bins. Use a shared 2-mm-scale grid for acquisition.
 if rows==5:cols=42
 cfg=dict(input_file='data/current.xls',input_format='legacy',point_base=8,mode='index_windows',continuous_only=True,width_mm=width,line_step_mm=1,columns=cols,row_windows_csv='estimated-row-windows.csv',title=name,short_title=name,rows=rows,x_speed_mm_s=v,nplc=nplc,reported_start_wait_seconds=wait,reported_motion_seconds=motion,model_cycle_seconds=cycle_seconds,turnaround_anchor_source_indices=turns.tolist(),estimated_sample_rate_per_row=rate.tolist(),color_limits_uA=[0,320 if rows==5 else 1050],interpretation_notes=['所有横扫窗口由信号重复结构及计时模型估计，无实测时间戳或位置记录。','仅保留单向正扫；回程、等待和尾段保留在原始波形中。','坐标为名义坐标；尚无Marker的实测尺寸标定。','用户报告Y随X速度变化但未实测：源表组采用Y=X的名义运动时间及0.9秒换轴停顿；绝对mm尺度仅近似，比较另用Marker归一化坐标。'])
 (case/'config.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
 data=reconstruct(case/'config.json');write_outputs(data,case/'results')
 print(name,len(a),'windows',list(zip(starts,ends)),'rate',np.median(rate))
