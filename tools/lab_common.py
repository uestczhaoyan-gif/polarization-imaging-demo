"""Small, hardware-independent helpers shared by the three lab tools."""
import csv
import hashlib
import json
import math
from pathlib import Path

EVENT_FIELDS = ['seq','mcu_ms','event','move','row','phase','axis','direction','distance_um','value']
CSV_FIELDS = EVENT_FIELDS + ['pc_monotonic_s','pc_utc']

def parse_event(line):
    fields=line.strip().split(',')
    if len(fields)!=11 or fields[0]!='E':
        raise ValueError('Invalid event frame')
    result=dict(zip(EVENT_FIELDS,fields[1:]))
    for key in EVENT_FIELDS:
        if key!='event':
            result[key]=int(result[key])
            if not 0<=result[key]<=0xffffffff:raise ValueError('Event integer outside uint32')
    if not result['event'].replace('_','').isalnum():raise ValueError('Invalid event name')
    return result

def read_events(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:
        data=list(csv.DictReader(stream))
    if not data:raise ValueError('Empty event log')
    previous=None
    for item in data:
        validated=parse_event('E,'+','.join(str(item[k]) for k in EVENT_FIELDS))
        item.update(validated)
        if previous is not None and item['seq']!=previous+1:
            raise ValueError('Event loss, duplicated frames or MCU reset; do not combine sessions')
        previous=item['seq']
        if item['event'] in ('FAIL','LOG_LOST','RX_LOST','MOVE_FAILED','ABORT_REQUEST'):
            raise ValueError('Fault/aborted log: retain raw file; not a complete valid scan')
        if item['event']=='MOTOR_RX_DROPPED' and item['value']:
            raise ValueError('Motor reply mailbox overwrite detected; inspect raw run, do not certify timing/position')
    if not any(x['event']=='RUN_BEGIN' for x in data) or not any(x['event']=='RUN_END' for x in data):
        raise ValueError('Missing RUN_BEGIN/RUN_END; run incomplete')
    return data

def movements(events):
    result=[];active=None
    for e in events:
        if e['event']=='MOVE_BEGIN':
            if active is not None:raise ValueError('Unclosed movement')
            active={'begin':e,'events':[e]}
        elif active is not None and e['move']==active['begin']['move']:
            active['events'].append(e)
            if e['event']=='MOVE_END':
                active['end']=e;result.append(active);active=None
    if active is not None or not result:raise ValueError('Incomplete movement records')
    return result

def finite(value,label):
    value=float(value)
    if not math.isfinite(value):raise ValueError(label+' must be finite')
    return value

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write_json(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

def fresh_directory(path):
    path=Path(path);path.mkdir(parents=True,exist_ok=False);return path
