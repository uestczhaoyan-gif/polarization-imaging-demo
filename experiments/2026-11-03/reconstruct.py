from pathlib import Path
import numpy as np
from scipy.ndimage import median_filter, gaussian_filter1d
from scipy.optimize import differential_evolution
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
S=Path(__file__).resolve().parent;O=S/'results'
raw=np.loadtxt(S/'data/current.xls',skiprows=1,usecols=0,encoding='gb18030')*1e9
ids=np.arange(len(raw))
labels=[line.split()[1] for line in (S/'data/current.xls').read_text(encoding='gb18030').splitlines()[1:] if line.strip()]
assert all(int(v,8)==i for i,v in enumerate(labels))
# Fit the reversal symmetry of the signal using the short spatial texture in both passes.
# Stopwatch provides only a prior on cycle/forward duration.
z=gaussian_filter1d(median_filter(raw,size=9),12)
z-=gaussian_filter1d(z,180)
rows=np.arange(40);u=np.arange(170,1831,18)
def cost(p):
    turn=p[0]+rows*p[1]
    a=np.interp(turn[:,None]-u,ids,z)
    b=np.interp(turn[:,None]+u,ids,z)
    return -np.sum(a*b)/(np.linalg.norm(a)*np.linalg.norm(b)+1e-20)
fit=differential_evolution(cost,[(2950,3900),(4400,4500)],seed=1103,tol=1e-7)
turns=fit.x[0]+rows*fit.x[1]
span=fit.x[1]*(40/1.5)/(2352.52/40)
stop=np.rint(turns).astype(int);start=np.rint(turns-span).astype(int)
assert start[0]>=0 and stop[-1]<len(raw)
edges=np.rint(start[:,None]+(stop-start)[:,None]*np.linspace(0,1,41)).astype(int)
im=np.array([[np.median(raw[a:b]) for a,b in zip(e[:-1],e[1:])] for e in edges])
np.savetxt(O/'current_nA.csv',im,delimiter=',',fmt='%.9g')
np.savetxt(O/'row_windows.csv',np.c_[rows,start,stop],header='row_zero_based,start_index,stop_index_exclusive',comments='',fmt='%d',delimiter=',')
np.savetxt(O/'pixel_to_points.csv',[(r,c,edges[r,c],edges[r,c+1],im[r,c]) for r,c in np.ndindex(im.shape)],header='row,col,start_index,stop_index_exclusive,median_nA',comments='',fmt=['%d','%d','%d','%d','%.9g'],delimiter=',')
fig,ax=plt.subplots(figsize=(12,4),layout='constrained')
ax.plot(ids,raw,lw=.28,color='#245778')
for a,b in zip(start,stop): ax.axvspan(a,b,color='green',alpha=.09,lw=0)
ax.set(xlabel='Original sample index (no timestamps)',ylabel='Current / nA',title='Full raw trace | green: estimated forward scan windows')
fig.savefig(O/'raw_current.png',dpi=165);plt.close(fig)
fig,ax=plt.subplots(figsize=(6,5),layout='constrained')
m=ax.imshow(im,extent=[0,40,40,0],interpolation='nearest',cmap='viridis')
ax.set(xlabel='Nominal X / mm (forward scan)',ylabel='Nominal Y / mm (row order)',title='Low-bias scan | median current per pixel')
fig.colorbar(m,ax=ax,label='Current / nA');fig.savefig(O/'reconstruction.png',dpi=180)
print('fit',fit.x,'score',-fit.fun,'points',len(raw),'windows',start[0],stop[0],start[-1],stop[-1],'points per pixel',np.diff(edges).min(),np.diff(edges).max(),'image range',im.min(),im.max())
