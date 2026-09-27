"""Make a measurement sheet from motor events, then analyze actual measured positions.

Commanded positions and driver status do not establish mechanical accuracy.
Blank observations never count as a passing speed trial.
"""
import argparse
import csv
from pathlib import Path
from statistics import mean,stdev
from lab_common import read_events,movements,finite,write_json,sha

COLUMNS=['move','repeat','axis','direction','phase','commanded_mm','measured_mm',
         'stable_yes_no','measured_motion_s','notes']

def template(events):
    config={e['event']:e['value'] for e in events}
    if config.get('EXPERIMENT') not in (2,3) or config.get('STAGE')!=3:
        raise ValueError('Requires completed 04 characterization experiment (mode 2 or 3)')
    legs=movements(events);position=0.;direction=legs[0]['begin']['direction'];axis=legs[0]['begin']['axis']
    rows=[]
    for leg in legs:
        e=leg['begin']
        if e['axis']!=axis:raise ValueError('Not a single-axis experiment')
        position+=(1 if e['direction']==direction else -1)*e['distance_um']/1000
        rows.append(dict(move=e['move'],repeat=e['row'],axis=axis,direction=e['direction'],phase=e['phase'],
                         commanded_mm=round(position,9),measured_mm='',stable_yes_no='',measured_motion_s='',notes=''))
    return rows

def analyze(events,rows,resolution,tolerance):
    expected=template(events)
    resolution=finite(resolution,'measurement resolution');tolerance=finite(tolerance,'tolerance')
    if resolution<=0 or tolerance<=0 or resolution>tolerance:raise ValueError('Require 0 < measurement resolution <= tolerance')
    if len(rows)!=len(expected):raise ValueError('Measurement rows must match event movements')
    errors=[];groups={};speeds=[];all_stable=True
    for actual,nominal,leg in zip(rows,expected,movements(events)):
        for key in ('move','repeat','axis','direction','phase'):
            if int(actual[key])!=nominal[key]:raise ValueError('Measurement identity mismatch: '+key)
        if abs(finite(actual['commanded_mm'],'command')-nominal['commanded_mm'])>1e-8:raise ValueError('Do not edit commanded coordinates')
        measured=finite(actual['measured_mm'],'measured_mm (relative to measured initial zero)')
        stable=actual['stable_yes_no'].strip().lower()
        if stable not in ('yes','no'):raise ValueError('Every movement needs an observed stable yes/no assessment')
        all_stable &= stable=='yes'
        error=measured-nominal['commanded_mm'];errors.append(error)
        groups.setdefault((nominal['commanded_mm'],nominal['direction']),[]).append(measured)
        if actual['measured_motion_s'].strip():
            dt=finite(actual['measured_motion_s'],'measured motion time')
            if dt<=0:raise ValueError('Measured motion time must be positive')
            speeds.append(leg['begin']['distance_um']/1000/dt)
    repeatability=[dict(commanded_mm=pos,direction=d,n=len(v),std_mm=stdev(v),range_mm=max(v)-min(v))
                   for (pos,d),v in groups.items() if len(v)>=3]
    config={e['event']:e['value'] for e in events};roundtrip=config['EXPERIMENT']==2
    adequate=roundtrip and len(expected)>=6 and bool(repeatability)
    passed=adequate and all_stable and max(abs(x) for x in errors)<=tolerance
    return dict(experiment=config['EXPERIMENT'],commanded_mm_s=config['RPM']*config['LEAD_UM']/60000,
                resolution_mm=resolution,tolerance_mm=tolerance,n_moves=len(rows),mean_error_mm=mean(errors),
                max_abs_error_mm=max(abs(x) for x in errors),repeatability=repeatability,
                measured_average_speeds_mm_s=speeds,observed_stable_all=all_stable,
                speed_trial_pass=passed,speed_trial_eligible=adequate,
                notice='Pass is conditional on this load, axis, travel, mounting, tolerance and observation. Not maximum rated speed or certified accuracy. Staircase tests do not qualify as speed trials.')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--events',required=True,type=Path)
    p.add_argument('--sheet',required=True,type=Path);p.add_argument('--report',type=Path)
    p.add_argument('--resolution-mm',type=float);p.add_argument('--tolerance-mm',type=float);args=p.parse_args()
    events=read_events(args.events)
    if not args.report:
        with args.sheet.open('x',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=COLUMNS);w.writeheader();w.writerows(template(events))
        print('Fill measured_mm relative to initial measured zero, stable_yes_no and optional independently measured motion times.')
    else:
        if args.report.exists():raise FileExistsError(args.report)
        with args.sheet.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
        report=analyze(events,rows,args.resolution_mm,args.tolerance_mm)
        report.update(events_sha256=sha(args.events),measurements_sha256=sha(args.sheet))
        write_json(args.report,report);print(report)

if __name__=='__main__':main()
