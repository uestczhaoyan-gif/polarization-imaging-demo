"""Split the published reconstruction by recorded scan direction; no new fitting."""
from pathlib import Path
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
CASE=Path(__file__).resolve().parents[1]
OUT=CASE/'results/direction-check';OUT.mkdir(exist_ok=True)
FAST=CASE.parent/'bidirectional-50mm-pitch-0p5mm-speed-10mmps'
def load(case):
 d=np.load(case/'results/reconstruction.npz');z=d['median_A']*1e6
 with (case/'estimated-row-windows.csv').open(encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
 forward=np.array([i for i,r in enumerate(rows) if r['direction']=='forward']);reverse=np.array([i for i,r in enumerate(rows) if r['direction']=='reverse'])
 assert z.shape==(100,100) and np.array_equal(forward,np.arange(0,100,2)) and np.array_equal(reverse,np.arange(1,100,2))
 # Published reverse rows already have their X samples placed in spatial order.
 lim=d['limits'];raw=d['raw_current_A'];expected=np.array([np.median(raw[a:b]) for a,b in lim.reshape(-1,2)]).reshape(z.shape)
 assert np.allclose(expected,d['median_A'],rtol=0,atol=1e-18)
 return z,forward,reverse
z,f,r=load(CASE)
np.savez_compressed(OUT/'direction_subsets.npz',all_current_uA=z,forward_current_uA=z[f],reverse_current_uA=z[r],forward_source_rows=f,reverse_source_rows=r,forward_y_mm=.25+.5*f,reverse_y_mm=.25+.5*r)
for name,ids in [('forward',f),('reverse',r)]:
 np.savetxt(OUT/(name+'_current_uA.csv'),z[ids],delimiter=',')
 with (OUT/(name+'_rows.csv')).open('w',newline='',encoding='utf-8-sig') as out:
  w=csv.writer(out);w.writerow(['subset_row_zero_based','original_row_zero_based','nominal_y_center_mm']);w.writerows((k,int(i),.25+.5*i) for k,i in enumerate(ids))
def draw(axes,z,f,r,prefix=''):
 for ax,values,title,extent in zip(axes,[z,z[f],z[r]],['All rows','Forward rows only','Reverse rows only'],[[0,50,50,0],[0,50,49.75,-.25],[0,50,50.25,.25]]):
  im=ax.imshow(values,extent=extent,cmap='viridis',vmin=0,vmax=650,interpolation='nearest')
  ax.set(title=prefix+title,xlabel='Nominal X / mm',ylabel='Nominal Y / mm',ylim=(50,0))
 return im
fig,axes=plt.subplots(1,3,figsize=(13,5),layout='constrained');im=draw(axes,z,f,r)
fig.colorbar(im,ax=axes,label='Median current / uA',shrink=.75)
fig.suptitle('1 mm/s | bidirectional | 50 x 50 mm | original row pitch 0.5 mm',fontsize=12)
fig.savefig(OUT/'directions.png',dpi=160);plt.close(fig)
fast,ff,fr=load(FAST)
fig,axes=plt.subplots(2,3,figsize=(13,9),layout='constrained')
im=draw(axes[0],z,f,r,'1 mm/s | ');draw(axes[1],fast,ff,fr,'10 mm/s | ')
fig.colorbar(im,ax=axes,label='Median current / uA',shrink=.75)
fig.savefig(OUT/'slow_fast_directions.png',dpi=160);plt.close(fig)
print('PASS: both original pixel medians verified; subsets copied exactly; direction labels checked against row windows.')
