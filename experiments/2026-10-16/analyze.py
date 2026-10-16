"""1016 analysis: immutable raw currents, explicit index windows and provenance.

Run from anywhere: python <this file>. No instrument timestamps are invented.
Registration fits ONLY peripheral markers; the C target is held out.
"""
from pathlib import Path
import json, csv
import numpy as np
from scipy.signal import find_peaks
from scipy.ndimage import map_coordinates
from scipy.optimize import differential_evolution
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
OUT=HERE/'comparisons';OUT.mkdir(exist_ok=True)

def save_csv(path, rows):
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def load(case):
    d=np.load(case/'results/reconstruction.npz')
    cfg=json.loads((case/'config.json').read_text(encoding='utf-8'))
    return d,cfg

def normalized(z):
    dark=np.percentile(z,5);bright=np.percentile(z,95)
    return (z-dark)/(bright-dark),float(dark),float(bright)

def crossing(a,p,q,level,rising,first=True):
    idx=np.arange(max(0,int(p)),min(len(a)-1,int(q)))
    good=(a[idx]<level)&(a[idx+1]>=level) if rising else (a[idx]>=level)&(a[idx+1]<level)
    cand=idx[good]
    if len(cand)==0:return np.nan
    i=cand[0 if first else -1]
    return i+(level-a[i])/(a[i+1]-a[i])

def overview(cases,name,vmax):
    fig,axs=plt.subplots(len(cases),2,figsize=(15,3*len(cases)),layout='constrained')
    for (case,label),axes in zip(cases,axs):
        d,cfg=load(case);raw=d['raw_current_A']*1e6;z=d['median_A']*1e6
        axes[0].plot(raw,lw=.5,color='#245778')
        limits=d['limits'];starts=limits[:,:,0].min(1);ends=limits[:,:,1].max(1)
        for i,(a,b) in enumerate(zip(starts,ends)):
            axes[0].axvspan(a,b,color='green',alpha=.1)
        axes[0].axvspan(ends[-1],len(raw),color='grey',alpha=.15)
        axes[0].set(title=label+' | full raw, green: used forward scans',xlabel='Source index (NOT measured time)',ylabel='Current / uA')
        im=axes[1].imshow(z,extent=[0,cfg['width_mm'],cfg['rows'],0],vmin=0,vmax=vmax,cmap='viridis',aspect='auto',interpolation='nearest')
        axes[1].set(title=label+' | estimated nominal map',xlabel='Nominal X / mm',ylabel='Nominal Y / mm')
    fig.colorbar(im,ax=axs[:,1],label='Median current / uA',shrink=.8)
    fig.savefig(OUT/name,dpi=160);plt.close(fig)

def acquisition():
    cases=[(HERE/'acquisition'/p,l) for p,l in [('A-v10-nplc0p1','A: 10 mm/s, NPLC 0.1'),('B-v10-nplc0p01','B: 10 mm/s, NPLC 0.01'),('C-v10-nplc1','C: 10 mm/s, NPLC 1'),('D-v1-nplc0p1','D: 1 mm/s, NPLC 0.1')]]
    overview(cases,'01_acquisition_overview.png',320)
    profiles={};rows=[];summaries=[];u=np.linspace(-.1,1.1,601)
    fig,axs=plt.subplots(2,2,figsize=(13,8),layout='constrained')
    for (case,label),ax in zip(cases,axs.flat):
        d,cfg=load(case);a=d['raw_current_A']*1e6
        pk,_=find_peaks(a,height=260,prominence=150,distance=len(a)//70)
        assert len(pk)==20
        z=[]
        for r in range(5):
            p0,p1=pk[4*r:4*r+2];span=p1-p0
            dark=np.median(a[int(p0+.15*span):int(p0+.30*span)])
            # Fixed local baseline region is valid on rows 2..5; row 1 is reported separately.
            bright=np.median(np.sort(a[p1-2:p1+3])[-3:]);scale=bright-dark
            left=crossing(a,p0,p0+.2*span,dark+.5*scale,False)
            right=crossing(a,p1,p1+.25*span,dark+.5*scale,False)
            assert np.isfinite(left+right)
            dist=right-left
            rise10=crossing(a,left+.05*dist,p1,dark+.1*scale,True)
            rise90=crossing(a,left+.05*dist,p1,dark+.9*scale,True)
            fall90=crossing(a,p0,p0+.2*span,dark+.9*scale,False)
            fall10=crossing(a,p0,p0+.2*span,dark+.1*scale,False)
            line=(np.interp(left+u*dist,np.arange(len(a)),a)-dark)/scale
            z.append(line)
            mm_per_point=cfg['width_mm']/(d['limits'][r,:,1].max()-d['limits'][r,:,0].min())
            rows.append(dict(case=case.name,row=r+1,left_anchor_source_index=left,right_anchor_source_index=right,anchor_distance_samples=dist,
                rise_10_90_samples=rise90-rise10,fall_90_10_samples=fall10-fall90,rise_width_fraction=(rise90-rise10)/dist,fall_width_fraction=(fall10-fall90)/dist,
                approximate_rise_width_mm=(rise90-rise10)*mm_per_point,approximate_fall_width_mm=(fall10-fall90)*mm_per_point,dark_uA=dark,bright_uA=bright))
        profiles[case.name]=np.array(z)
        for r,line in enumerate(z):ax.plot(u,line,label=f'row {r+1}',lw=1.1 if r else 2)
        ax.set(title=label,xlabel='Relative coordinate: two falling edges at 0 and 1',ylabel='Normalized current',ylim=(-.12,1.15));ax.legend(fontsize=8);ax.grid(alpha=.2)
        limits=d['limits'];counts=limits[:,:,1]-limits[:,:,0]
        summaries.append(dict(case=case.name,raw_points=len(a),forward_points=int(counts.sum()),return_wait_tail_points=int(len(a)-counts.sum()),last_forward_stop=int(limits.max()),columns=counts.shape[1],points_per_pixel_min=int(counts.min()),points_per_pixel_max=int(counts.max()),integration_ms=20*cfg['nplc'],integration_travel_mm=cfg['x_speed_mm_s']*cfg['nplc']/50,estimated_cycle_sample_rate_hz=float(np.median(cfg['estimated_sample_rate_per_row']))))
    fig.savefig(OUT/'02_acquisition_marker_profiles.png',dpi=170);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(13,4.5),layout='constrained')
    for case,label in cases:
        z=profiles[case.name];axs[0].plot(u,z[0],label=label);axs[1].plot(u,np.median(z[1:],axis=0),label=label)
    for ax,title in zip(axs,['First row: broad transition persists at all settings','Rows 2-5: median profile']):
        ax.set(title=title,xlabel='Relative marker coordinate',ylabel='Normalized current');ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.savefig(OUT/'03_acquisition_setting_comparison.png',dpi=170);plt.close(fig)
    ref=profiles['D-v1-nplc0p1'];corr=[]
    for key,z in profiles.items():
        for r in range(5):corr.append(dict(case=key,row=r+1,correlation_to_D=float(np.corrcoef(z[r],ref[r])[0,1]),normalized_MAE_to_D=float(np.mean(abs(z[r]-ref[r])))))
    save_csv(OUT/'acquisition_edge_metrics.csv',rows);save_csv(OUT/'acquisition_summary.csv',summaries);save_csv(OUT/'acquisition_shape_comparison.csv',corr)

def registration():
    cases=[(HERE/'registration'/f'light{k}',f'Light setting {k}%') for k in [20,40,60]]
    overview(cases,'04_registration_original.png',1050)
    data=[load(c)[0] for c,l in cases];z=[d['median_A']*1e6 for d in data]
    norm=[normalized(im)[0] for im in z]
    yy,xx=np.indices((20,55));x=xx+.5;y=yy+.5
    # Predeclared marker-only regions: left protrusions and right bar. C is held out.
    marker=((x<8)|((x>30)&(x<37)))&(y<18)
    train=marker&(yy%2==0);test=marker&(yy%2==1)
    target=(x>9)&(x<29)&(y>1)&(y<18)
    plan=dict(reference='light20',parameters='source_x=27.5+scale*(reference_x-27.5)+dx; source_y=reference_y+dy',bounds=dict(dx_mm=[-2,2],dy_mm=[-2,2],scale=[.95,1.05]),fit_mask='x<8 or 30<x<37, y<18; even row indices',held_out_marker='same ROI, odd row indices',held_out_target='9<x<29, 1<y<18',model='one global X scale + X/Y translation, no rotation or per-row warping',seed=1016)
    (OUT/'registration-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    def resample(im,p):
        dx,dy,s=p
        return map_coordinates(im,[y+dy-.5,27.5+s*(x-27.5)+dx-.5],order=1,mode='nearest')
    params=[np.array([0.,0.,1.])];metrics=[]
    for j in range(3):
        if j:
            fit=differential_evolution(lambda p:np.mean((resample(norm[j],p)[train]-norm[0][train])**2),[(-2,2),(-2,2),(.95,1.05)],seed=1016,maxiter=100,popsize=12,tol=1e-8)
            params.append(fit.x)
        p=params[j];reg=resample(norm[j],p)
        metric=dict(light_percent=[20,40,60][j],dx_mm=float(p[0]),dy_mm=float(p[1]),x_scale=float(p[2]))
        for label,mask in [('train_marker',train),('heldout_marker',test),('heldout_C',target)]:
            metric[label+'_MAE_before']=float(np.mean(abs(norm[j][mask]-norm[0][mask])))
            metric[label+'_MAE_after']=float(np.mean(abs(reg[mask]-norm[0][mask])))
        metrics.append(metric)
    save_csv(OUT/'registration_metrics.csv',metrics)
    # Map COMMON PIXEL FOOTPRINTS to original raw sample intervals. No RGB warping.
    # Vertical weights represent row-strip overlap, not newly measured Y positions.
    fused=[];provenance=[];counts_all=[]
    for j,(d,p) in enumerate(zip(data,params)):
        dx,dy,s=p;raw=d['raw_current_A']*1e6;lim=d['limits'];lo=lim[:,:,0].min(1);hi=lim[:,:,1].max(1)
        image=np.full((20,55),np.nan);counts=np.zeros((20,55),int)
        for r,c in np.ndindex(image.shape):
            xl=27.5+s*(c-27.5)+dx;xh=xl+s;yl=r+dy;yh=yl+1
            if xl<0 or xh>55 or yl<0 or yh>20:continue
            values=[];weights=[];entries=[]
            for rr in range(int(np.floor(yl)),min(20,int(np.ceil(yh)))):
                weight=max(0,min(yh,rr+1)-max(yl,rr))
                if weight<1e-10:continue
                a=int(np.ceil(lo[rr]+xl/55*(hi[rr]-lo[rr])));b=int(np.ceil(lo[rr]+xh/55*(hi[rr]-lo[rr])))
                if b<=a:break
                value=float(np.median(raw[a:b]));values.append(value);weights.append(weight);counts[r,c]+=b-a
                entries.append(dict(light_percent=[20,40,60][j],common_row=r,common_col=c,source_row=rr,start_source_index=a,stop_source_index_exclusive=b,sample_count=b-a,y_overlap_weight=weight,row_interval_median_uA=value))
            if weights and abs(sum(weights)-1)<1e-8:
                image[r,c]=np.dot(weights,values);provenance.extend(entries)
        fused.append(image);counts_all.append(counts)
    valid=np.all(np.isfinite(fused),axis=0)
    grid=[]
    for r,c in np.ndindex(valid.shape):
        entry=dict(row=r,col=c,x_center_mm=c+.5,y_center_mm=r+.5,common_valid=bool(valid[r,c]))
        for j,k in enumerate([20,40,60]):entry.update({f'I{k}_uA':fused[j][r,c],f'n{k}':counts_all[j][r,c]})
        grid.append(entry)
    save_csv(OUT/'common_grid_currents.csv',grid);save_csv(OUT/'common_pixel_source_intervals.csv',provenance)
    np.savez_compressed(OUT/'registered_currents.npz',current_uA=np.array(fused),common_valid=valid,transforms=np.array(params),original_current_uA=np.array(z))
    fig,axs=plt.subplots(2,3,figsize=(15,7),layout='constrained')
    for j in range(3):
        for r,img in enumerate([z[j],fused[j]]):
            im=axs[r,j].imshow(img,extent=[0,55,20,0],vmin=0,vmax=1050,cmap='viridis',interpolation='nearest',aspect='auto')
            axs[r,j].set(title=f'{[20,40,60][j]}% | '+('original' if r==0 else 'common grid; raw-current aggregation'),xlabel='Reference nominal X / mm',ylabel='Y / mm')
    fig.colorbar(im,ax=axs,label='Current / uA',shrink=.8);fig.savefig(OUT/'05_registration_common_grid.png',dpi=170);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(13,5),layout='constrained')
    for j,color in enumerate(['#1f77b4','#ff7f0e','#2ca02c']):
        axs[0].contour(x,y,norm[j],levels=[.5],colors=[color],linewidths=1)
        nn=resample(norm[j],params[j]);axs[1].contour(x,y,nn,levels=[.5],colors=[color],linewidths=1)
    for ax,title in zip(axs,['Before registration','Marker-based registration (C target not fitted)']):ax.set(title=title,xlim=(0,40),ylim=(20,0),xlabel='Nominal X / mm',ylabel='Y / mm')
    fig.savefig(OUT/'06_registration_edge_overlay.png',dpi=170);plt.close(fig)
    # Geometry validation from original high-density raw row profiles: central C
    # left edge, rows 5..12. It was not part of the marker objective.
    edges=[]
    for j,d in enumerate(data):
        cfg=json.loads((cases[j][0]/'config.json').read_text(encoding='utf-8'))
        raw=d['raw_current_A']*1e6;lim=d['limits'];lo=lim[:,:,0].min(1);hi=lim[:,:,1].max(1)
        for r in range(5,13):
            a=raw[lo[r]:hi[r]];n=len(a);b=np.percentile(a,5);h=np.percentile(a,90)
            q=crossing(a,n*12/55,n*23/55,b+.5*(h-b),True)
            xpos=q/n*55;dx,dy,s=params[j]
            edges.append(dict(light_percent=[20,40,60][j],source_row=r,source_y_mm=r+.5,reference_y_mm=r+.5-dy,edge_x_before_mm=xpos,edge_x_after_mm=27.5+(xpos-27.5-dx)/s))
    save_csv(OUT/'heldout_C_edge_positions.csv',edges)
    # Constant bright ROI, away from Marker and C edges. No per-image intensity scaling.
    roi=valid&(x>=20)&(x<25)&(y>=6)&(y<12)
    stats=[]
    for j in range(3):
        values=fused[j][roi];dark=normalized(z[j])[1]
        stats.append(dict(light_percent=[20,40,60][j],roi='20<=X<25,6<=Y<12 nominal mm',pixels=int(len(values)),median_uA=float(np.median(values)),q25_uA=float(np.quantile(values,.25)),q75_uA=float(np.quantile(values,.75)),approx_dark_uA=dark,dark_subtracted_median_uA=float(np.median(values)-dark)))
    save_csv(OUT/'aligned_bright_roi.csv',stats)
    print('REGISTRATION',json.dumps(metrics));print('ROI',json.dumps(stats));print('Common pixels',valid.sum())

if __name__=='__main__':
    acquisition();registration()
