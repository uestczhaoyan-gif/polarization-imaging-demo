"""Map laptop manual SourceMeter-time marks to MCU seconds using serial clock exchanges."""
import argparse
import csv
from pathlib import Path
from lab_common import finite,write_json,sha
from align_motion import fit_anchors

def map_marks(sync_path,marks_path,output):
    with Path(sync_path).open(encoding='utf-8-sig',newline='') as f:sync=list(csv.DictReader(f))
    with Path(marks_path).open(encoding='utf-8-sig',newline='') as f:marks=list(csv.DictReader(f))
    if len(sync)<2 or len(marks)<2:raise ValueError('Need at least two clock exchanges and two genuine meter-time marks')
    x=[finite(r['mcu_s'],'mcu_s') for r in sync];y=[finite(r['pc_mid_s'],'pc_mid_s') for r in sync]
    if any(b<=a for a,b in zip(x,x[1:])) or any(b<=a for a,b in zip(y,y[1:])):raise ValueError('Clocks must increase')
    mx=sum(x)/len(x);my=sum(y)/len(y);slope=sum((a-mx)*(b-my) for a,b in zip(x,y))/sum((a-mx)**2 for a in x)
    offset=my-slope*mx;rows=[]
    for mark in marks:
        pc=finite(mark['pc_monotonic_s'],'manual PC time');meter=finite(mark['meter_s'],'meter_s')
        if not min(y)<=pc<=max(y):raise ValueError('Manual marks must lie within recorded PC synchronization range')
        rows.append(((pc-offset)/slope,meter))
    with Path(output).open('x',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(['mcu_s','meter_s']);w.writerows(rows)
    fit_anchors(output)
    write_json(str(output)+'.json',dict(pc_seconds_per_mcu_second=slope,
        max_clock_fit_residual_s=max(abs(a*slope+offset-b) for a,b in zip(x,y)),
        max_half_roundtrip_s=max(finite(r['half_rtt_s'],'rtt') for r in sync),
        sync_sha256=sha(sync_path),marks_sha256=sha(marks_path),
        warning='Serial midpoint assumes approximate path symmetry. Manual keypress/display delay is additional and unmeasured. No hardware synchronization.'))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--sync',type=Path,required=True)
    p.add_argument('--marks',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();map_marks(a.sync,a.marks,a.output)

if __name__=='__main__':main()
