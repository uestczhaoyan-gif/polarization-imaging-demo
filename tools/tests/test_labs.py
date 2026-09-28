import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import types
import queue
import io
from contextlib import redirect_stdout

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from lab_common import EVENT_FIELDS,parse_event,read_events,movements
from prepare_lab import configuration,prepare
from align_motion import make_windows,fit_anchors
from analyze_stage import template,analyze
from map_clocks import map_marks
import collect_motion

def events(experiment=1):
    result=[]
    def emit(name,tick=0,move=0,row=0,phase=0,direction=0,distance=0,value=0):
        result.append(dict(seq=len(result),mcu_ms=tick,event=name,move=move,row=row,phase=phase,axis=2,
                           direction=direction,distance_um=distance,value=value))
    for name,value in [('BOOT',1),('EXPERIMENT',experiment),('STAGE',3),('LEAD_UM',1000),('RPM',60),('ACC',0)]:emit(name,value=value)
    emit('RUN_BEGIN',100)
    phases=[5,9,6,5,9,6] if experiment==1 else [5,9]*3
    for i,phase in enumerate(phases,1):
        row=(i-1)//(3 if experiment==1 else 2)+1
        args=dict(move=i,row=row,phase=phase,direction=int(phase==9),distance=1000)
        emit('MOVE_BEGIN',i*2000,**args,value=60)
        emit('ACK',i*2000+10,**args,value=2)
        emit('DRIVER_REACHED_RX',i*2000+1000,**args)
        emit('MOVE_END',i*2000+1150,**args)
    emit('RUN_END',15000)
    return result

class LabTests(unittest.TestCase):
    def test_collector_with_fake_serial_never_touches_hardware(self):
        data=events();split=next(i for i,e in enumerate(data) if e['event']=='RUN_BEGIN')
        ready=dict(data[0],event='READY');data.insert(split,ready)
        for i,e in enumerate(data):e['seq']=i
        def wire(rows):return ''.join('E,'+','.join(str(e[k]) for k in EVENT_FIELDS)+'\r\n' for e in rows).encode()
        boot=wire(data[:split+1]);motion=wire(data[split+1:]);writes=[]
        class FakeSerial:
            def __init__(self,**kwargs):self.is_open=False;self.buffer=boot
            def open(self):self.is_open=True
            def close(self):self.is_open=False
            @property
            def in_waiting(self):return len(self.buffer)
            def read(self,n):chunk=self.buffer[:n];self.buffer=self.buffer[n:];return chunk
            def write(self,value):
                writes.append(value)
                if value==b'G':self.buffer+=motion
        serial=types.ModuleType('serial');serial.Serial=FakeSerial
        serial_tools=types.ModuleType('serial.tools');serial_tools.list_ports=types.SimpleNamespace(comports=lambda:[])
        for commands,success in ([('g',0),('q',1)],True),([('q',0)],False):
            with tempfile.TemporaryDirectory() as temp:
                out=Path(temp)/'session';q=queue.Queue()
                for cmd in commands:q.put(cmd)
                with patch.dict(sys.modules,{'serial':serial,'serial.tools':serial_tools}),patch.object(sys,'argv',['collect','--port','FAKE','--output',str(out)]),patch.object(collect_motion.queue,'Queue',return_value=q),patch.object(collect_motion.threading,'Thread'),redirect_stdout(io.StringIO()):
                    if success:collect_motion.main()
                    else:
                        with self.assertRaises(SystemExit):collect_motion.main()
                manifest=json.loads((out/'session.json').read_text(encoding='utf-8'))
                self.assertEqual(manifest['complete'],success)
                if success:self.assertEqual(len(movements(read_events(out/'events.csv'))),6)
                else:self.assertEqual(writes[-1],b'!')

    def test_event_parser_and_loss_rejected(self):
        self.assertEqual(parse_event('E,0,10,BOOT,0,0,0,0,0,0,1')['mcu_ms'],10)
        for text in ('E,0,0','E,-1,10,BOOT,0,0,0,0,0,0,1','E,0,10,BOOT,0,0,0,0,0,0,NaN'):
            with self.assertRaises(ValueError):parse_event(text)
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'events.csv'
            for mutate in ('normal','gap','fault','truncated','mailbox'):
                data=events()
                if mutate=='gap':data.pop(7)
                if mutate=='fault':data[8]['event']='FAIL'
                if mutate=='truncated':data.pop()
                if mutate=='mailbox':data[8].update(event='MOTOR_RX_DROPPED',value=1)
                with p.open('w',newline='') as f:
                    w=csv.DictWriter(f,fieldnames=EVENT_FIELDS);w.writeheader();w.writerows(data)
                if mutate=='normal':self.assertEqual(len(movements(read_events(p))),6)
                else:
                    with self.assertRaises(ValueError):read_events(p)

    def test_windows_exclude_returns_and_steps(self):
        windows,report=make_windows(events(),(1,0,0,20,0),'driver',0)
        self.assertEqual(windows,[(2,3,'forward'),(8,9,'forward')])
        nominal,_=make_windows(events(),(1.001,3,0,20,.02),'nominal',0,True)
        self.assertEqual(nominal[0][2],'reverse')
        self.assertAlmostEqual(nominal[0][0],5.002)
        self.assertIn('NOT',report['warning'])

    def test_ambiguous_arrival_and_extrapolation_rejected(self):
        for kind in ('missing','duplicate','anchor','acc'):
            data=events();anchor=(1,0,0,20,0)
            if kind=='missing':data=[e for e in data if e['event']!='DRIVER_REACHED_RX']
            if kind=='duplicate':data.insert(10,dict(data[9]))
            if kind=='anchor':anchor=(1,0,3,20,0)
            if kind=='acc':next(e for e in data if e['event']=='ACC')['value']=10
            with self.assertRaises(ValueError):make_windows(data,anchor,'nominal' if kind=='acc' else 'driver',0)

    def test_affine_clocks_and_manual_marks(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);(p/'sync.csv').write_text('mcu_s,pc_mid_s,half_rtt_s\n0,100,.01\n10,110.01,.02\n20,120.02,.01\n')
            (p/'marks.csv').write_text('pc_monotonic_s,meter_s\n101.001,0\n119.019,18\n')
            map_marks(p/'sync.csv',p/'marks.csv',p/'anchors.csv')
            slope,offset,lo,hi,_=fit_anchors(p/'anchors.csv')
            self.assertAlmostEqual(slope,1);self.assertAlmostEqual(offset,-1)
            self.assertAlmostEqual(lo,1);self.assertAlmostEqual(hi,19)
            (p/'marks.csv').write_text('pc_monotonic_s,meter_s\n90,0\n119.019,18\n')
            with self.assertRaises(ValueError):map_marks(p/'sync.csv',p/'marks.csv',p/'bad.csv')

    def test_profiles_validate_and_subpulse_rejected(self):
        for p in (ROOT/'labs').glob('*/settings.json'):configuration(json.loads(p.read_text(encoding='utf-8')))
        profile={'lab':{'LAB_EXPERIMENT':3,'LAB_LOG_ENABLE':1,'LAB_TEST_DISTANCE_UM':5}}
        configuration(profile)
        for changes in ({'LAB_TEST_DISTANCE_UM':1},{'LAB_TEST_DISTANCE_UM':50000},{'LAB_TEST_REPEATS':0}):
            wrong=json.loads(json.dumps(profile));wrong['lab'].update(changes)
            with self.assertRaises(ValueError):configuration(wrong)

    def test_independent_project_keeps_sources_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            original=(ROOT/'firmware/Core/Inc/snake_scan_config.h').read_bytes()
            out=prepare({'title':'Test','scan':{'SCAN_MODE':1}},Path(temp)/'one')
            self.assertEqual(len(list((out/'firmware/MDK-ARM').glob('*.uvprojx'))),4)
            self.assertTrue((out/'firmware/Core/Src/lab_io.c').exists())
            self.assertEqual(original,(ROOT/'firmware/Core/Inc/snake_scan_config.h').read_bytes())
            self.assertFalse(json.loads((out/'prepared-config.json').read_text(encoding='utf-8'))['flashed'])
            with self.assertRaises(FileExistsError):prepare({},out)

    def test_observation_required_and_speed_pass_is_conditional(self):
        data=events(2);rows=template(data)
        with self.assertRaises(ValueError):analyze(data,rows,.001,.01)
        for row in rows:
            row['measured_mm']=str(row['commanded_mm']+.002);row['stable_yes_no']='yes'
        report=analyze(data,rows,.001,.01)
        self.assertTrue(report['speed_trial_pass']);self.assertAlmostEqual(report['mean_error_mm'],.002)
        self.assertEqual(len(report['repeatability']),2)
        rows[0]['stable_yes_no']='no'
        self.assertFalse(analyze(data,rows,.001,.01)['speed_trial_pass'])
        rows[0]['measured_mm']='nan'
        with self.assertRaises(ValueError):analyze(data,rows,.001,.01)

if __name__=='__main__':unittest.main()
