"""复现文档中的敏感性与混合像素统计；不把变化率当成图像正确率。"""
from pathlib import Path
import json
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from snake_scan.pipeline import reconstruct,build_edges,aggregate


def main():
    data=reconstruct(Path(__file__).with_name('config.json'))
    meta=data['metadata'];cfg=meta['config'].copy()
    cfg.update(mode='constant',samples_per_row=meta['samples_per_row'],start_point=meta['start_point_estimate'])
    raw=data['raw_current_A'];reference=data['binary'];variants=[]
    for name,t,delta,gap in [('threshold_8_uA',8,0,.031),('threshold_16_uA',16,0,.031),
                            ('no_turnaround_exclusion',12,0,0),('turnaround_5_percent',12,0,.05),
                            ('row_period_minus_8',12,-8,.031),('row_period_plus_8',12,8,.031)]:
        variant=cfg.copy();variant.update(samples_per_row=cfg['samples_per_row']+delta,turnaround_fraction=gap)
        edges,reverse,_=build_edges(raw,None,variant,ROOT,t*1e-6)
        image=aggregate(raw,edges,reverse,t*1e-6)['binary']
        if image.shape!=reference.shape:raise ValueError('变体行数改变，不能直接比较像素比例。')
        variants.append({'variant':name,'changed_pixels':int((image!=reference).sum()),
                         'changed_pixels_percent':float((image!=reference).mean()*100)})
    isolated=[]
    for r in range(1,len(reference)-1):
        for c in range(1,reference.shape[1]-1):
            if all(reference[rr,cc]!=reference[r,c] for rr,cc in [(r-1,c),(r+1,c),(r,c-1),(r,c+1)]):
                isolated.append([r,c])
    f=data['high_fraction']
    summary={'sensitivity':variants,'mixed_pixels_20_to_80_percent':int(((f>=.2)&(f<=.8)).sum()),
             'interior_pixels_opposite_to_all_four_neighbors':isolated,
             'note':'Fixed other parameters; no refitting per variant. These are diagnostics, not errors versus a calibrated ground truth.'}
    out=ROOT/'outputs/z_tape/analysis.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
