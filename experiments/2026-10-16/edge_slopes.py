"""Slopes of the original plotted segments crossing the 50% edge, rows 2-5."""
import analyze as a
import numpy as np
from scipy.signal import find_peaks
cases=['A-v10-nplc0p1','B-v10-nplc0p01','C-v10-nplc1','D-v1-nplc0p1'];out=[]
for name in cases:
 d,cfg=a.load(a.HERE/'acquisition'/name);raw=d['raw_current_A']*1e6;lim=d['limits']
 pk,_=find_peaks(raw,height=260,prominence=150,distance=len(raw)//70)
 assert len(pk)==20
 for r in range(1,5):
  p0,p1=pk[4*r:4*r+2];span=p1-p0
  dark=np.median(raw[int(p0+.15*span):int(p0+.30*span)])
  bright=np.median(np.sort(raw[p1-2:p1+3])[-3:]);scale=bright-dark;z=(raw-dark)/scale
  mm=cfg['width_mm']/(lim[r,:,1].max()-lim[r,:,0].min())
  left=a.crossing(z,p0,p0+.2*span,.5,False)
  for kind,lo,hi,rising in [('fall',p0,p0+.2*span,False),('rise',left+.05*span,p1,True)]:
   t=a.crossing(z,lo,hi,.5,rising);i=int(np.floor(t));k=(z[i+1]-z[i])/mm
   assert min(z[i],z[i+1])<=.5<=max(z[i],z[i+1])
   # Sensitivity: secant over the SAME +/-0.25 mm display interval.
   u0=np.interp(t-.25/mm,np.arange(len(z)),z);u1=np.interp(t+.25/mm,np.arange(len(z)),z)
   out.append(dict(case=name,row=r+1,edge=kind,source_i=i,source_i_next=i+1,x_i_mm=(i-t)*mm,x_next_mm=(i+1-t)*mm,sample_spacing_mm=mm,normalized_i=z[i],normalized_next=z[i+1],slope_per_mm=k,current_slope_uA_per_mm=k*scale,secant_plusminus_0p25mm_per_mm=(u1-u0)/.5))
a.save_csv(a.OUT/'edge_slopes_rows2to5.csv',out)
summary=[]
for name in cases:
 for kind in ['fall','rise']:
  q=[r for r in out if r['case']==name and r['edge']==kind];v=np.array([r['slope_per_mm'] for r in q])
  summary.append(dict(case=name,edge=kind,median_slope_per_mm=np.median(v),min_slope_per_mm=v.min(),max_slope_per_mm=v.max(),median_sample_spacing_mm=np.median([r['sample_spacing_mm'] for r in q]),median_fixed_window_secant_per_mm=np.median([r['secant_plusminus_0p25mm_per_mm'] for r in q])))
a.save_csv(a.OUT/'edge_slopes_summary.csv',summary)
for r in summary:print(r)
