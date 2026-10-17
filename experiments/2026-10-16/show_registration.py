"""Geometry presentation. Normalization is display-only, never applied to exported currents."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy.spatial import cKDTree
S=Path(__file__).resolve().parent;O=S/'comparisons'
d=np.load(O/'registered_currents.npz');orig=d['original_current_uA'];reg=d['current_uA'];valid=d['common_valid'];params=d['transforms']
y,x=np.indices(valid.shape);x=x+.5;y=y+.5
norm=[]
for j in range(3):
 lo,hi=np.percentile(orig[j],[5,95]);norm.append([(orig[j]-lo)/(hi-lo),(reg[j]-lo)/(hi-lo)])
colors=['#0072B2','#D55E00','#009E73'];labels=['20%','40%','60%']
fig,axs=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
for stage,ax in enumerate(axs):
 rgb=np.stack([np.clip(norm[j][stage],0,1) for j in range(3)],axis=-1)
 if stage:rgb[~valid]=.25
 ax.imshow(rgb,extent=[0,55,20,0],aspect='equal',interpolation='nearest')
 ax.set(title=['Before: independent maps','After: common-grid currents'][stage],xlabel='Nominal X / mm',ylabel='Y / mm')
fig.suptitle('RGB overlay: R=20%, G=40%, B=60%; display-normalized only. Color fringes are NOT pure position error.',fontsize=10)
fig.savefig(O/'08_rgb_overlay.png',dpi=180);plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(12,4.5),layout='constrained');segments={}
for stage,ax in enumerate(axs):
 for j in range(3):
  cs=ax.contour(x,y,norm[j][stage],levels=[.5],colors=[colors[j]],linewidths=1.2)
  parts=[v for v in cs.allsegs[0] if len(v)>1];dense=[]
  for part in parts:
   for a,b in zip(part[:-1],part[1:]):
    t=np.linspace(0,1,max(2,int(np.linalg.norm(b-a)/.025)+1));dense.extend(a[None,:]+t[:,None]*(b-a))
  segments[stage,j]=np.array(dense)
 ax.set(title=['Before registration','After registration'][stage],xlim=(0,40),ylim=(20,0),aspect='equal',xlabel='Nominal X / mm',ylabel='Y / mm')
 ax.legend(handles=[Line2D([0],[0],color=c,label=l) for c,l in zip(colors,labels)],loc='upper right')
fig.suptitle('50% normalized edge contours: compare geometry, not absolute brightness',fontsize=11)
fig.savefig(O/'09_geometry_overlay.png',dpi=180);plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(12,4),layout='constrained');rows=[]
for j,ax in zip([1,2],axs):
 dx,dy,s=params[j];ux=27.5+s*(x-27.5)+dx-x;uy=np.full_like(y,dy);mag=np.hypot(ux,uy);mag[~valid]=np.nan
 im=ax.imshow(mag,extent=[0,55,20,0],vmin=0,vmax=.8,cmap='viridis',aspect='equal',interpolation='nearest')
 ax.quiver(x[::3,::5],y[::3,::5],ux[::3,::5],uy[::3,::5],angles='xy',scale_units='xy',scale=.25,color='white',width=.004)
 ax.set(title=labels[j]+' source position relative to 20% grid',xlabel='Nominal X / mm',ylabel='Y / mm')
 for r,c in np.ndindex(valid.shape):
  rows.append([labels[j],r,c,x[r,c],y[r,c],ux[r,c],uy[r,c],mag[r,c]])
fig.colorbar(im,ax=axs,label='Model correspondence displacement / mm',shrink=.75)
fig.suptitle('Applied coordinate mapping, NOT remaining error; arrows enlarged 4x',fontsize=11)
fig.savefig(O/'10_correspondence_displacement.png',dpi=180);plt.close(fig)
import csv
with (O/'correspondence_displacement.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['light','row','col','reference_x_mm','reference_y_mm','source_minus_reference_x_mm','source_minus_reference_y_mm','magnitude_mm']);w.writerows(rows)
fig,axs=plt.subplots(2,2,figsize=(12,8),layout='constrained');summary=[]
for stage in range(2):
 ref=segments[stage,0];ref=ref[(ref[:,0]>9)&(ref[:,0]<29)&(ref[:,1]>1)&(ref[:,1]<18)]
 for jj,j in enumerate([1,2]):
  pts=segments[stage,j];pts=pts[(pts[:,0]>9)&(pts[:,0]<29)&(pts[:,1]>1)&(pts[:,1]<18)]
  dist=cKDTree(pts).query(ref)[0];ax=axs[stage,jj]
  ax.set_facecolor('#eeeeee');ax.plot(pts[:,0],pts[:,1],'.',color='#b0b0b0',ms=1)
  im=ax.scatter(ref[:,0],ref[:,1],c=dist,s=8,vmin=0,vmax=1,cmap='magma')
  ax.set(title=labels[j]+' vs 20% | '+['before','after'][stage],xlim=(8,30),ylim=(19,0),aspect='equal',xlabel='Nominal X / mm',ylabel='Y / mm')
  summary.append([labels[j],['before','after'][stage],float(np.median(dist)),float(np.percentile(dist,90))])
fig.colorbar(im,ax=axs,label='Nearest contour distance / mm (one-way)',shrink=.75)
fig.suptitle('C target edge-distance map; uniform interiors have no identifiable positional residual',fontsize=11)
fig.savefig(O/'11_target_edge_distance.png',dpi=180);plt.close(fig)
with (O/'target_contour_distance_summary.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['light','stage','median_mm','p90_mm']);w.writerows(summary)
print(summary)
