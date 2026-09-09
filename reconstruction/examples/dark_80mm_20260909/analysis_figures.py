"""比较分行相位敏感性；不根据照片选相位，不改变主结果。"""
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
from snake_scan.core import read_data, otsu_threshold
from snake_scan.pipeline import aggregate


def main():
    raw,_,_,_=read_data(HERE/'data/raw_export.xls')
    windows=np.genfromtxt(HERE/'estimated_windows.csv',delimiter=',',skip_header=1,usecols=(0,1),dtype=int)
    output=HERE/'../../outputs/dark_80mm_20260909'
    output.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(1,3,figsize=(12,4.5),layout='constrained')
    for ax,shift in zip(axes,[-15,0,15]):
        edges=np.ceil([np.linspace(a+shift,b+shift,41) for a,b in windows]).astype(int)
        z=aggregate(raw,edges,np.arange(40)%2==1,otsu_threshold(raw))['binary']
        ax.imshow(z,cmap=ListedColormap(['#173d65','#f0ba57']),vmin=0,vmax=1,
                  extent=[0,80,80,0],interpolation='nearest')
        ax.set(title=f'Window shift: {shift:+d} samples',xlabel='Nominal X / mm',ylabel='Nominal Y / mm')
        ax.axhspan(6,10,fill=False,edgecolor='#c42b40',lw=1.2,ls='--')
    fig.suptitle('Timing sensitivity, not independent measurements; red: suspect interval')
    fig.savefig(output/'03_timing_sensitivity.png',dpi=170); plt.close(fig)
    anchors=np.genfromtxt(HERE/'waveform_anchors.csv',delimiter=',',skip_header=1)
    fig,ax=plt.subplots(figsize=(10,3.5),layout='constrained')
    ax.plot(np.arange(2,21),anchors[1:,2],'o-',color='#173d65')
    ax.axhline(np.median(anchors[1:,2]),ls='--',color='#777',label='median = 971.5 points')
    ax.scatter([3],[786.5],color='#c42b40',zorder=3)
    ax.set(xlabel='Ending anchor number (1-based)',ylabel='Interval / samples',
           title='Repeated waveform intervals: no measured time or position')
    ax.legend(); fig.savefig(output/'04_anchor_intervals.png',dpi=170); plt.close(fig)


if __name__=='__main__':main()
