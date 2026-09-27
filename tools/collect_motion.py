"""Record MCU events. No SourceMeter access. G starts one armed firmware run; ! requests stop."""
import argparse
import csv
from datetime import datetime,timezone
import json
from pathlib import Path
import queue
import threading
import time
from lab_common import CSV_FIELDS,parse_event,write_json,sha

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--project',type=Path,help='Built/flashed experiment folder for configuration snapshot')
    args=parser.parse_args()
    try:
        import serial
        from serial.tools import list_ports
    except ImportError:raise SystemExit('Install: python -m pip install pyserial')
    if not args.port:
        for p in list_ports.comports():print(p.device,p.description)
        args.port=input('USB-TTL COM port (USART3, not motor USART1): ').strip()
    folder=args.output or Path('local/motion-logs')/datetime.now().strftime('%Y%m%d-%H%M%S')
    folder.mkdir(parents=True,exist_ok=False)
    manifest={'started_utc':datetime.now(timezone.utc).isoformat(),'port':args.port,'baud':115200,
              'complete':False,'source_meter_connected':False,'clock':'PC monotonic; MCU HAL_GetTick ms',
              'warnings':['Motor arrival receipt is not exact physical position/time.']}
    if args.project:
        for name in ('snake_scan_config.h','lab_config.h'):
            src=args.project/'firmware/Core/Inc'/name
            (folder/name).write_bytes(src.read_bytes());manifest[name+'_sha256']=sha(src)
    write_json(folder/'session.json',manifest)
    commands=queue.Queue()
    def keyboard():
        while True:
            try:cmd=input().strip().lower()
            except EOFError:return
            commands.put((cmd,time.monotonic()))
            if cmd in ('q','!'):return
    threading.Thread(target=keyboard,daemon=True).start()
    print('Logging to',folder.resolve())
    print('Open recorder BEFORE board reset. g starts; m <meter_seconds> records a manual time mark; q exits (! requests stop).')
    print('After RUN_END, record a final meter mark, wait for SYNC, then q. Never unplug motor cables powered.')
    ready=False;running=False;last_seq=None;pending=None;last_ping=0.;finished=False;buffer=b'';boot_seen=False
    # Explicitly disable handshake lines before opening; separate USB-TTL only.
    port=serial.Serial(port=None,baudrate=115200,timeout=.05,write_timeout=1)
    port.dtr=False;port.rts=False;port.port=args.port
    try:
        port.open()
        with (folder/'events.csv').open('x',newline='',encoding='utf-8') as ef, (folder/'raw.jsonl').open('x',encoding='utf-8') as raw, (folder/'pc_sync.csv').open('x',newline='',encoding='utf-8') as sf, (folder/'manual_marks.csv').open('x',newline='',encoding='utf-8') as mf:
            writer=csv.DictWriter(ef,fieldnames=CSV_FIELDS);writer.writeheader()
            sync=csv.writer(sf);sync.writerow(['mcu_s','pc_mid_s','pc_send_s','pc_receive_s','half_rtt_s'])
            marks=csv.writer(mf);marks.writerow(['pc_monotonic_s','meter_s'])
            while True:
                chunk=port.read(1024)
                if chunk:buffer+=chunk
                if len(buffer)>8192:raise ValueError('Serial line too long / wrong port or baud')
                while b'\n' in buffer:
                    line,buffer=buffer.split(b'\n',1)
                    now=time.monotonic();utc=datetime.now(timezone.utc).isoformat()
                    raw.write(json.dumps({'pc_monotonic_s':now,'pc_utc':utc,'hex':line.hex()})+'\n');raw.flush()
                    try:e=parse_event(line.decode('ascii'))
                    except (ValueError,UnicodeError):
                        if last_seq is None:continue # opening in the middle of a frame
                        raise ValueError('Malformed event after recording began')
                    if not boot_seen and e['event']!='BOOT':continue
                    if last_seq is not None and e['seq']!=last_seq+1:raise ValueError('Lost event or MCU reset; start a fresh session')
                    last_seq=e['seq'];writer.writerow(dict(e,pc_monotonic_s=now,pc_utc=utc));ef.flush()
                    event=e['event']
                    if event=='BOOT':boot_seen=True
                    if event=='READY':
                        if not ready:print('READY: verify stage direction/travel, then type g to start.')
                        ready=True
                    if event=='SYNC':
                        if pending is not None:
                            sync.writerow([e['mcu_ms']/1000,(pending+now)/2,pending,now,(now-pending)/2]);sf.flush();pending=None
                            if finished:print('Post-run clock exchange saved. Record final meter mark, wait another 5 s, then q.')
                    if event in ('MOVE_BEGIN','MOVE_END','FAIL','RUN_END'):print(e)
                    if event=='RUN_BEGIN':running=True
                    if event=='RUN_END':manifest['complete']=True;finished=True;running=False
                    if event in ('FAIL','LOG_LOST','RX_LOST','MOVE_FAILED'):
                        raise ValueError('MCU reported '+event)
                if not commands.empty():
                    cmd,keytime=commands.get()
                    if cmd in ('q','!'):
                        if not finished:port.write(b'!');manifest['stop_requested']=True
                        break
                    if cmd.startswith('m '):
                        from lab_common import finite
                        marks.writerow([keytime,finite(cmd[2:],'manual meter time')]);mf.flush()
                        print('Manual mark saved at Enter time; includes human reaction/display delay.')
                    if cmd=='g':
                        if not boot_seen or not ready or running or finished:print('Need BOOT then READY, and only one start per reset. No command sent.')
                        elif pending is not None:print('Clock exchange pending; retry g shortly.')
                        else:port.write(b'G');running=True
                now=time.monotonic()
                if pending is not None and now-pending>10:
                    raise TimeoutError('No clock reply in 10 s; no more sync requests to avoid mispairing a late reply')
                if ready and pending is None and now-last_ping>=5:
                    pending=time.monotonic();port.write(b'?');last_ping=pending
    except KeyboardInterrupt:
        manifest['stop_requested']=True
        if port.is_open:port.write(b'!')
    except Exception as error:
        manifest['error']=str(error)
        if port.is_open:
            try:port.write(b'!')
            except Exception:pass
        print('RECORDING STOPPED:',error)
    finally:
        port.close();manifest['closed_utc']=datetime.now(timezone.utc).isoformat()
        manifest['notice']='Software ! is best effort; communication loss cannot guarantee stop. Use hardware power cutoff.'
        write_json(folder/'session.json',manifest)
    print('Saved:',folder.resolve(),'complete=',manifest['complete'])
    if not manifest['complete'] or 'error' in manifest:raise SystemExit(1)

if __name__=='__main__':main()
