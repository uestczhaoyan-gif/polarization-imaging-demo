"""Summarize filled offline measurement plans; no observations are inferred from commands."""
import argparse
import csv
import json
from pathlib import Path
from lab_common import finite,sha,write_json

def summarize(config,rows,resolution=None,tolerance=None):
    sweep=config['sweep'];plan=sweep['plan'];kind=sweep['kind']
    if len(rows)!=len(plan):raise ValueError('测量表行数与生成的计划不一致；未执行的行请留空，不要删除')
    for expected,actual in zip(plan,rows):
        for key in ('move','stage','repeat','phase','pulses','rpm','actual_speed_mm_s','commanded_position_mm'):
            if key=='phase':matches=expected[key]==actual[key]
            else:matches=abs(finite(expected[key],key)-finite(actual[key],key))<=1e-12
            if not matches:raise ValueError('不要修改计划列：'+key)
    if kind=='minimum_distance':
        resolution=finite(resolution,'resolution');tolerance=finite(tolerance,'tolerance')
        if resolution<=0 or tolerance<resolution:raise ValueError('需填写量具分辨率和不小于该分辨率的位移误差容差')
    results=[]
    for level in sweep['levels']:
        group=[r for r in rows if int(r['stage'])==level['stage']]
        complete=all(r['completed_yes_no'].strip().lower()=='yes' for r in group)
        stable=all(r['stable_yes_no'].strip().lower()=='yes' for r in group)
        result=dict(stage=level['stage'],actual_distance_mm=level['actual_distance_mm'],actual_speed_mm_s=level['actual_speed_mm_s'],
                    completed=complete,observed_stable=stable,passed=False)
        if kind=='minimum_distance' and complete and stable:
            measured=[finite(r['measured_position_mm'],'实测位置不可空白') for r in group if r['phase']!='return']
            steps=[b-a for a,b in zip(measured,measured[1:])]
            result['measured_steps_mm']=steps
            result['passed']=all(d>2*resolution and abs(d-level['actual_distance_mm'])<=tolerance for d in steps)
            result['criterion']='Every measured forward increment >2 instrument resolution units and within declared error tolerance; not a calibrated uncertainty certificate.'
        elif kind!='minimum_distance':result['passed']=complete and stable
        results.append(result)
    good=[r for r in results if r['passed']]
    key='actual_distance_mm' if kind=='minimum_distance' else 'actual_speed_mm_s'
    selected=(max if kind=='maximum_speed' else min)((r[key] for r in good),default=None)
    return dict(kind=kind,levels=results,best_tested_passing_value=selected,unit='mm' if kind=='minimum_distance' else 'mm/s',
                notice='Only the tested settings under the recorded conditions. No automatic mechanical sensing; blanks/unfinished trials never pass. Repeat boundary levels and both axes.')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True)
    p.add_argument('--measurements',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--resolution-mm',type=float);p.add_argument('--tolerance-mm',type=float);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    configuration=a.project/'prepared-config.json'
    config=json.loads(configuration.read_text(encoding='utf-8'))
    with a.measurements.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    result=summarize(config,rows,a.resolution_mm,a.tolerance_mm)
    result.update(config_sha256=sha(configuration),measurements_sha256=sha(a.measurements))
    write_json(a.output,result);print('Saved:',a.output)

if __name__=='__main__':main()
