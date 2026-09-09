"""生成已知答案的非均匀采样例子；不代表实测数据。

两行都是 [低、高、高]；第 2 行按 reverse 采集，以检验方向。
采样时间不等间隔，时间窗分别 [1,4)、[5,8)。
"""
from pathlib import Path
import csv
import json
import numpy as np

folder=Path(__file__).resolve().parent
rng=np.random.default_rng(7)
times=np.r_[0,np.cumsum(rng.uniform(.025,.045,300))]
times=times[times<=9]
current=np.full(len(times),4e-6)
for a,b,reverse in [(1,4,False),(5,8,True)]:
    coordinate=b-times if reverse else times-a
    current[(times>=a)&(times<b)&(coordinate>=1)]=24e-6
current+=rng.normal(0,.08e-6,len(times))
with (folder/'data.csv').open('w',newline='',encoding='utf-8') as f:
    writer=csv.writer(f);writer.writerow(['point','time_s','current_A'])
    writer.writerows(zip(range(len(times)),times,current))
(folder/'rows.csv').write_text('start_s,stop_s,direction\n1,4,forward\n5,8,reverse\n',encoding='utf-8')
config={'input_file':'data.csv','input_format':'csv','mode':'time_windows',
        'row_windows_csv':'rows.csv','width_mm':6,'line_step_mm':2,'columns':3,
        'threshold_uA':12,'minimum_samples_per_pixel':10,'max_sample_gap_seconds':.05,
        'output_dir':'../../outputs/synthetic','title':'合成验证：非均匀时间戳与行方向'}
(folder/'config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(folder/'expected_binary.csv').write_text('0,1,1\n0,1,1\n',encoding='utf-8')
