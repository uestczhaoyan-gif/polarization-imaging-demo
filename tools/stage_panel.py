"""Offline, finite characterization of minimum displacement and stable speed limits."""
import copy
from datetime import datetime
from decimal import Decimal
import tkinter as tk
from tkinter import ttk,messagebox
from prepare_lab import ROOT,prepare,configuration
from stage_sweep import KINDS,DEFAULTS

LABELS={'最小有效位移':'minimum_distance','最低平稳速度':'minimum_speed','最高平稳速度':'maximum_speed'}
FIELDS=[('axis','测试轴：0=X / 1=Y'),('xdir','X 去程方向：0/1'),('ydir','Y 去程方向：0/1'),
        ('levels','档位列表：位移用 mm，速度用 mm/s；逗号分隔'),
        ('distance','速度测试单程距离 mm'),('speed','位移测试速度 mm/s'),
        ('preload','位移测试同向预走 mm'),('repeats','每档小步数 / 往返次数'),
        ('dwell','每次运动后停留 s'),('pause','档间准备时间 s'),
        ('xsafe','X 起点到去程方向可用行程 mm'),('ysafe','Y 起点到去程方向可用行程 mm'),
        ('logging','日志：0=离线自动运行 / 1=串口输入 g 启动')]

class StagePanel:
    def __init__(self,window,profile):
        self.window=window;self.profile=copy.deepcopy(profile);self.entries={}
        window.title('平台三项测试 · 离线自动分档');window.geometry('850x800')
        box=ttk.Frame(window,padding=16);box.pack(fill='both',expand=True)
        ttk.Label(box,text='只测试：最小有效位移、最低平稳速度、最高平稳速度',font=('',14)).grid(row=0,columnspan=2,sticky='w')
        ttk.Label(box,text='默认不需要USB转TTL。生成工程后编译下载；04工程复位、倒计时后自动执行一次。\n自动执行 ≠ 自动判定；请用量具/录像填写生成的测量表。').grid(row=1,columnspan=2,pady=8,sticky='w')
        self.kind=tk.StringVar(value=next(k for k,v in LABELS.items() if v==profile['sweep']['kind']))
        selector=ttk.Combobox(box,textvariable=self.kind,values=list(LABELS),state='readonly')
        selector.grid(row=2,columnspan=2,sticky='ew',pady=6);selector.bind('<<ComboboxSelected>>',self.change_kind)
        _,_,record=configuration(profile);s=record['scan'];l=record['lab'];o=profile['sweep']
        initial=dict(axis=l['LAB_TEST_AXIS'],xdir=s['X_FIRST_PASS_DIRECTION'],ydir=s['Y_STEP_DIRECTION'],
                     levels=', '.join(map(str,o['levels'])),distance=o.get('distance_mm','1'),speed=s['SCAN_SPEED_UM_PER_SEC']/1000,
                     preload=o.get('preload_mm','.2'),repeats=l['LAB_TEST_REPEATS'],dwell=l['LAB_TEST_DWELL_MS']/1000,
                     pause=o.get('stage_pause_ms',5000)/1000,xsafe=s['X_AXIS_MAX_SAFE_TRAVEL_UM']/1000,
                     ysafe=s['Y_AXIS_MAX_SAFE_TRAVEL_UM']/1000,logging=l['LAB_LOG_ENABLE'])
        for row,(key,label) in enumerate(FIELDS,3):
            ttk.Label(box,text=label).grid(row=row,column=0,sticky='w',pady=5)
            var=tk.StringVar(value=str(initial[key]));self.entries[key]=var
            widget=ttk.Combobox(box,textvariable=var,values=['0','1'],state='readonly') if key in ('axis','xdir','ydir','logging') else ttk.Entry(box,textvariable=var)
            widget.grid(row=row,column=1,sticky='ew')
        row=len(FIELDS)+3
        ttk.Button(box,text='校验档位、生成独立工程与空白测量表',command=self.generate).grid(row=row,columnspan=2,pady=10)
        self.status=tk.StringVar(value='硬件导程、细分与加速度沿用主配置。方向须通过小行程检查确认。')
        ttk.Label(box,textvariable=self.status,wraplength=790).grid(row=row+1,columnspan=2,sticky='w',pady=8)
        box.columnconfigure(1,weight=1)

    def change_kind(self,event=None):
        defaults=DEFAULTS[LABELS[self.kind.get()]]
        self.entries['levels'].set(', '.join(defaults['levels']))
        self.entries['distance'].set(defaults['distance_mm']);self.entries['preload'].set(defaults['preload_mm'])

    def get_profile(self):
        p=copy.deepcopy(self.profile);kind=LABELS[self.kind.get()];e={k:v.get().strip() for k,v in self.entries.items()}
        def integer(key,scale=1):
            v=Decimal(e[key])*scale
            if not v.is_finite() or v!=v.to_integral_value():raise ValueError('次数/方向须为整数；时间精确到毫秒，普通配置精确到微米')
            return int(v)
        p['title']='03 '+self.kind.get()+' · 自动分档'
        p.setdefault('scan',{}).update(X_FIRST_PASS_DIRECTION=integer('xdir'),Y_STEP_DIRECTION=integer('ydir'),
            SCAN_SPEED_UM_PER_SEC=integer('speed',1000),X_AXIS_MAX_SAFE_TRAVEL_UM=integer('xsafe',1000),Y_AXIS_MAX_SAFE_TRAVEL_UM=integer('ysafe',1000))
        p.setdefault('lab',{}).update(LAB_EXPERIMENT=KINDS[kind],LAB_LOG_ENABLE=integer('logging'),LAB_TEST_AXIS=integer('axis'),
            LAB_TEST_REPEATS=integer('repeats'),LAB_TEST_DWELL_MS=integer('dwell',1000))
        p['sweep']=dict(kind=kind,levels=[x.strip() for x in e['levels'].replace('，',',').split(',')],
                        distance_mm=e['distance'],preload_mm=e['preload'],stage_pause_ms=integer('pause',1000))
        return p

    def generate(self):
        try:
            p=self.get_profile();_,_,r=configuration(p)
            out=prepare(p,ROOT/'local/lab-projects'/datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
            sweep=r['sweep']
            self.status.set('已生成（尚未烧录）：'+str(out)+'\n一脉冲名义位移 '+f"{sweep['minimum_command_mm']:.9g}"+' mm；预计至少 '+f"{sweep['ideal_seconds_without_controller_overhead']/60:.1f}"+' 分钟，另加控制器确认开销。\n实际脉冲/RPM与顺序见 prepared-config.json 和 measurement-plan.csv。')
        except Exception as error:messagebox.showerror('未生成',str(error))
