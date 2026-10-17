"""Rows 2-5 only: inspect original edge samples, no image interpolation."""
import analyze as a
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
cases=['A-v10-nplc0p1','B-v10-nplc0p01','C-v10-nplc1','D-v1-nplc0p1']
fig,axs=plt.subplots(4,2,figsize=(12,13),layout='constrained');out=[]
for i,name in enumerate(cases):
 d,cfg=a.load(a.HERE/'acquisition'/name);raw=d['raw_current_A']*1e6
 pk,_=find_peaks(raw,height=260,prominence=150,distance=len(raw)//70)
 for r in range(1,5):
  p0,p1=pk[4*r:4*r+2];span=p1-p0
  dark=np.median(raw[int(p0+.15*span):int(p0+.30*span)])
  bright=np.median(np.sort(raw[p1-2:p1+3])[-3:]);z=(raw-dark)/(bright-dark)
  mm=cfg['width_mm']/(d['limits'][r,:,1].max()-d['limits'][r,:,0].min())
  left=a.crossing(z,p0,p0+.2*span,.5,False)
  for j,(kind,lo,hi,rising) in enumerate([('bright-to-dark',p0,p0+.2*span,False),('dark-to-bright',left+.05*span,p1,True)]):
   levels=[.1,.5,.9] if rising else [.9,.5,.1]
   t=[a.crossing(z,lo,hi,v,rising) for v in levels]
   ids=np.arange(max(0,int(t[1]-2/mm)),min(len(raw),int(t[1]+2/mm)+1))
   axs[i,j].plot((ids-t[1])*mm,z[ids],'.-',ms=2,lw=.8,label=f'row {r+1}')
   out.append(dict(case=name,row=r+1,edge=kind,width_mm=(t[2]-t[0])*mm,before50_mm=(t[1]-t[0])*mm,after50_mm=(t[2]-t[1])*mm,width_samples=t[2]-t[0]))
 for j in range(2):
  axs[i,j].set(title=name+' | '+['bright to dark','dark to bright'][j],xlim=(-1.5,1.5),ylim=(-.08,1.08),xlabel='Nominal distance from own 50% crossing / mm; scan ->',ylabel='Normalized original current')
  axs[i,j].axvline(0,color='grey',ls=':');axs[i,j].grid(alpha=.2);axs[i,j].legend(fontsize=8)
fig.savefig(a.OUT/'07_rows2to5_edge_review.png',dpi=160)
a.save_csv(a.OUT/'rows2to5_edge_review.csv',out)
for name in cases:
 for kind in ['bright-to-dark','dark-to-bright']:
  rows=[v for v in out if v['case']==name and v['edge']==kind]
  print(name,kind,'width mm',round(np.median([v['width_mm'] for v in rows]),3),'post/pre50',round(np.median([v['after50_mm']/v['before50_mm'] for v in rows]),2))
