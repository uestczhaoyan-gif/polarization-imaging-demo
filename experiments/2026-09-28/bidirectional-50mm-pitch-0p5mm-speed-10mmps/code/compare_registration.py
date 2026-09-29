from pathlib import Path
import json,sys,csv,hashlib
import numpy as np
from scipy.optimize import differential_evolution
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'reconstruction/snake_scan').is_dir())
sys.path.insert(0,str(ROOT/'reconstruction'))
from snake_scan.pipeline import aggregate
from snake_scan.continuous_report import write_outputs
CASE=ROOT/'experiments/2026-09-28/bidirectional-50mm-pitch-0p5mm-speed-10mmps'
OUT=ROOT/'local/registration-check'
OUT.mkdir(parents=True,exist_ok=True)
D=np.load(CASE/'results/reconstruction.npz')
raw=D['raw_current_A'];limits=D['limits'];a=limits[:,:,0].min(1);b=limits[:,:,1].max(1);length=b-a;center=(a+b)/2
reverse=np.arange(100)%2==1
# Photo supplies only the weak prior that nearby rows through the two windows
# should usually have similar profiles. Do not fit the photo or draw its edges.
# Disjoint adjacent-row pairs: train and test interleaved in the inner region.
train=np.arange(20,60,4);test=np.arange(22,62,4)
roi=slice(8,80) # nominal X 4..40 mm, avoids bright exterior on the right
(OUT/'plan.json').write_text(json.dumps(dict(input_sha256=hashlib.sha256((CASE/'raw/current.xls').read_bytes()).hexdigest(),training_pair_first_rows=train.tolist(),held_out_pair_first_rows=test.tolist(),roi_columns=[8,80],phase_fraction_bounds=[-.08,.08],duration_scale_bounds=[.8,1.2],metric='mean absolute adjacent-row current difference; uA; lower is more consistent, not positional ground truth',stop='one bounded two-parameter fit; no row-specific warping'),indent=2),encoding='utf-8')
def windows(phase=0,scale=1):
 c=center+phase*length
 return c-scale*length/2,c+scale*length/2

def preview(phase,scale):
 l,h=windows(phase,scale)
 idx=l[:,None]+(np.arange(100)[None,:]+.5)/100*(h-l)[:,None]
 z=np.interp(idx,np.arange(len(raw)),raw)*1e6
 z[reverse]=z[reverse,::-1]
 return z

def error(z,pairs):return float(np.mean(np.abs(z[pairs,roi]-z[pairs+1,roi])))
phasefit=differential_evolution(lambda p:error(preview(p[0],1),train),[(-.08,.08)],seed=928,maxiter=50,popsize=12,tol=1e-7)
fullfit=differential_evolution(lambda p:error(preview(*p),train),[(-.08,.08),(.8,1.2)],seed=928,maxiter=60,popsize=12,tol=1e-7)
variants=[('original',0,1,100),('coarser_x',0,1,50),('phase_only',float(phasefit.x[0]),1,100),('phase_and_duration',*map(float,fullfit.x),100)]
results={};metrics=[]
for name,phase,scale,cols in variants:
 l,h=windows(phase,scale);edges=np.ceil(l[:,None]+np.arange(cols+1)[None,:]/cols*(h-l)[:,None]).astype(int)
 assert edges.min()>=0 and edges.max()<=len(raw)
 res=aggregate(raw,edges,reverse,None)
 # Original published limits use ceil of integer windows. Preserve them exactly.
 if name=='original':
  res={k:D[k] for k in D.files if k not in ('raw_current_A','file_point_decimal','file_point_original')}
 z=res['median_A']*1e6;results[name]=z
 zz=z if cols==100 else np.repeat(z,2,axis=1)
 metrics.append(dict(variant=name,phase_fraction=phase,nominal_phase_mm=phase*50,window_duration_scale=scale,columns=cols,train_MAE_uA=error(zz,train),heldout_MAE_uA=error(zz,test)))
 meta=json.loads((CASE/'results/metadata.json').read_text(encoding='utf-8'))
 cfg=meta['config'];cfg['columns']=cols;cfg['title']=name;cfg['short_title']=name;cfg['interpretation_notes']=['探索性配准对照，保留原始电流；参数来自训练行连续性，不是实测机械修正。'];meta['windows']=np.stack([edges[:,0],edges[:,-1]],1).tolist();meta['notes']=cfg['interpretation_notes'];meta['points_used']=int((res['sample_row']>=0).sum());meta['points_excluded']=len(raw)-meta['points_used'];cnt=np.diff(res['limits'],axis=2);meta['points_per_pixel_min']=int(cnt.min());meta['points_per_pixel_max']=int(cnt.max());meta['columns']=cols
 data=dict(raw_current_A=raw,file_point_decimal=D['file_point_decimal'],file_point_original=D['file_point_original'],time_s=None,metadata=meta,**res)
 write_outputs(data,OUT/name)
with (OUT/'comparison.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=metrics[0].keys());w.writeheader();w.writerows(metrics)
fig,axes=plt.subplots(1,4,figsize=(18,5),layout='constrained')
for ax,(name,z),metric in zip(axes,results.items(),metrics):
 im=ax.imshow(z,extent=[0,50,50,0],vmin=0,vmax=650,cmap='viridis',interpolation='nearest');ax.set(title=f"{name}\nHeld-out MAE: {metric['heldout_MAE_uA']:.1f} uA",xlabel='Nominal X / mm',ylabel='Nominal Y / mm')
fig.colorbar(im,ax=axes,label='Median current / uA',shrink=.7)
fig.savefig(OUT/'comparison.png',dpi=170);plt.close(fig)
print(json.dumps(metrics,indent=2))

# Direction subsets preserve currents; each now has 1 mm vertical sampling.
z=D['median_A']*1e6
fig,axes=plt.subplots(1,3,figsize=(13,5),layout='constrained')
for ax,values,title,extent in zip(axes,[z,z[::2],z[1::2]],
        ['All rows','Forward rows only','Reverse rows only'],
        [[0,50,50,0],[0,50,49.75,-.25],[0,50,50.25,.25]]):
    im=ax.imshow(values,extent=extent,cmap='viridis',vmin=0,vmax=650,interpolation='nearest')
    ax.set(title=title,xlabel='Nominal X / mm',ylabel='Nominal Y / mm',ylim=(50,0))
fig.colorbar(im,ax=axes,label='Median current / uA',shrink=.75)
fig.savefig(OUT/'directions.png',dpi=160)
plt.close(fig)
