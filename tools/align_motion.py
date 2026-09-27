"""Convert logged scan legs to reconstruction windows using user-supplied MCU/meter time anchors."""
import argparse
import csv
from pathlib import Path
from lab_common import finite,read_events,movements,fresh_directory,write_json,sha

def fit_anchors(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    if len(rows)<2:raise ValueError('At least two measured time correspondences required; do not invent anchors')
    x=[finite(r['mcu_s'],'mcu_s') for r in rows];y=[finite(r['meter_s'],'meter_s') for r in rows]
    if any(b<=a for a,b in zip(x,x[1:])) or any(b<=a for a,b in zip(y,y[1:])):raise ValueError('Anchors must increase in both clocks')
    mx=sum(x)/len(x);my=sum(y)/len(y)
    slope=sum((a-mx)*(b-my) for a,b in zip(x,y))/sum((a-mx)**2 for a in x)
    offset=my-slope*mx
    residual=max(abs(slope*a+offset-b) for a,b in zip(x,y))
    if slope<=0:raise ValueError('Invalid clock slope')
    return slope,offset,min(x),max(x),residual

def make_windows(events,anchors,source,latency,first_reverse=False):
    slope,offset,lo,hi,residual=anchors
    config={e['event']:e['value'] for e in events if e['event'] in ('ACC','LEAD_UM','EXPERIMENT')}
    # Profile defaults can be captured after MCU boot: require metadata rather than guessing.
    if config.get('EXPERIMENT') not in (0,1):raise ValueError('This is not an imaging scan, or boot metadata missing. Reconnect before reset.')
    legs=[m for m in movements(events) if m['begin']['phase']==5]
    if not legs:raise ValueError('No imaging X legs')
    result=[];first_dir=legs[0]['begin']['direction']
    for i,m in enumerate(legs):
        begin=m['begin'];end=m['end'];start=begin['mcu_ms']/1000+latency
        if begin['row']!=i+1:raise ValueError('Non-contiguous imaging rows')
        if source=='nominal':
            if config.get('ACC')!=0 or not config.get('LEAD_UM'):raise ValueError('Nominal mode requires recorded ACC=0 and lead')
            speed=begin['value']*config['LEAD_UM']/60
            if speed<=0:raise ValueError('Invalid command speed')
            stop=start+begin['distance_um']/speed
        else:
            arrivals=[e for e in m['events'] if e['event']=='DRIVER_REACHED_RX' and start<e['mcu_ms']/1000<=end['mcu_ms']/1000]
            acks=[e for e in m['events'] if e['event']=='ACK' and e['value']==2]
            if len(arrivals)!=1 or not acks:raise ValueError('Need exactly one arrival plus acceptance for each row; inspect raw events')
            stop=arrivals[0]['mcu_ms']/1000
        if start<lo or stop>hi:raise ValueError('Anchors must bracket every selected window; extrapolation refused')
        if stop<=start or stop>end['mcu_ms']/1000:raise ValueError('Window outside completed movement')
        reverse=(begin['direction']!=first_dir)^first_reverse
        result.append((slope*start+offset,slope*stop+offset,'reverse' if reverse else 'forward'))
    if any(b[0]<a[1] for a,b in zip(result,result[1:])):raise ValueError('Overlapping windows')
    return result,dict(slope=slope,offset_s=offset,max_anchor_residual_s=residual,
                       position_assumption='uniform motion within selected row; neither method measures carriage position',
                       endpoint_source=source,start_latency_s=latency,
                       warning='Two anchors have zero fit residual by construction; this is NOT measured synchronization accuracy.')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--events',type=Path,required=True);p.add_argument('--anchors',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--window-source',choices=['nominal','driver'],required=True)
    p.add_argument('--start-latency-s',type=float,required=True,help='Measured/declared delay from MOVE_BEGIN log timestamp to effective scan start')
    p.add_argument('--first-row-reverse',action='store_true')
    p.add_argument('--accept-estimated-position',action='store_true',required=True)
    args=p.parse_args()
    latency=finite(args.start_latency_s,'latency')
    if latency<0:raise ValueError('latency must be nonnegative')
    windows,report=make_windows(read_events(args.events),fit_anchors(args.anchors),args.window_source,latency,args.first_row_reverse)
    out=fresh_directory(args.output)
    with (out/'row_windows.csv').open('x',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(['start_s','stop_s','direction']);w.writerows(windows)
    report.update(events_sha256=sha(args.events),anchors_sha256=sha(args.anchors),rows=len(windows))
    write_json(out/'alignment.json',report)
    print('Saved row_windows.csv. Use reconstruction mode=time_windows; these remain model-based position estimates.')

if __name__=='__main__':main()
