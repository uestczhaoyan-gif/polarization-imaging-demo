"""Three experiment presets; prepare source copies, never flash or start motors."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import ttk,messagebox
from decimal import Decimal
from prepare_lab import ROOT,prepare,configuration

FIELDS=[('scan','SCAN_MODE','扫描：0 双向 / 1 单向',1),
        ('scan','MASK_SCAN_WIDTH_UM','宽度 mm',1000),('scan','MASK_SCAN_HEIGHT_UM','高度 mm',1000),
        ('scan','Y_SPEED_UM_PER_SEC','Y 速度 mm/s',1000),
        ('scan','SCAN_LINE_STEP_UM','行距 mm',1000),('scan','SCAN_SPEED_UM_PER_SEC','X 速度 mm/s',1000),
        ('scan','X_FIRST_PASS_DIRECTION','X 去程：0 CW / 1 CCW',1),('scan','Y_STEP_DIRECTION','Y 去程：0 CW / 1 CCW',1),
        ('scan','X_AXIS_MAX_SAFE_TRAVEL_UM','X 当前可用行程 mm',1000),('scan','Y_AXIS_MAX_SAFE_TRAVEL_UM','Y 当前可用行程 mm',1000),
        ('lab','LAB_EXPERIMENT','实验：0 扫描 / 1 日志扫描 / 2 往返 / 3 阶梯',1),
        ('lab','LAB_LOG_ENABLE','电脑日志：0 关闭 / 1 开启',1),('lab','LAB_TEST_AXIS','单轴测试：0 X / 1 Y',1),
        ('lab','LAB_TEST_DISTANCE_UM','单轴每次距离 mm',1000),('lab','LAB_TEST_REPEATS','单轴重复 / 阶梯次数',1),
        ('lab','LAB_TEST_DWELL_MS','每次停留 秒',1000)]

class App:
    def __init__(self,window,profile):
        self.window=window;self.profile=profile;self.prepared=None;self.entries={}
        window.title('平移台实验工作台 — '+profile.get('title',''));window.geometry('760x800')
        box=ttk.Frame(window,padding=16);box.pack(fill='both',expand=True)
        ttk.Label(box,text=profile.get('title',''),font=('',15)).grid(row=0,columnspan=2,sticky='w')
        ttk.Label(box,text='生成独立工程副本；不自动烧录，不发送运动指令。\n单轴参数仅在 04 工程生效；01 不运动，02/03 为固定小行程扫描。').grid(row=1,columnspan=2,pady=8,sticky='w')
        _,_,record=configuration(profile)
        for row,(group,key,label,scale) in enumerate(FIELDS,2):
            ttk.Label(box,text=label).grid(row=row,column=0,sticky='w',pady=3)
            var=tk.StringVar(value=f'{record[group][key]/scale:g}');self.entries[(group,key)]=(var,scale)
            choices={'SCAN_MODE':['0','1'],'LAB_EXPERIMENT':['0','1','2','3'],'LAB_LOG_ENABLE':['0','1'],'LAB_TEST_AXIS':['0','1']}
            widget=ttk.Combobox(box,textvariable=var,values=choices[key],state='readonly') if key in choices else ttk.Entry(box,textvariable=var)
            widget.grid(row=row,column=1,sticky='ew')
        row=len(FIELDS)+2
        ttk.Button(box,text='校验并生成独立工程',command=self.generate).grid(row=row,columnspan=2,pady=12)
        ttk.Button(box,text='为刚生成的工程打开日志收集器',command=self.collect).grid(row=row+1,columnspan=2)
        self.status=tk.StringVar(value='硬件参数沿用主配置。可在 settings.json 中指定导程、细分和加速度。')
        ttk.Label(box,textvariable=self.status,wraplength=690).grid(row=row+2,columnspan=2,pady=12,sticky='w')
        box.columnconfigure(1,weight=1)

    def generate(self):
        try:
            profile=json.loads(json.dumps(self.profile))
            for (group,key),(var,scale) in self.entries.items():
                v=Decimal(var.get())*scale
                if not v.is_finite() or v!=v.to_integral_value():raise ValueError('输入须能精确换算为整数 μm / ms')
                profile.setdefault(group,{})[key]=int(v)
            out=ROOT/'local/lab-projects'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
            self.prepared=prepare(profile,out)
            _,_,record=configuration(profile);derived=record['derived']
            self.status.set('已生成（尚未烧录）：'+str(out)+'\n实际指令：'+str(derived['rpm'])+' RPM，'+f"{derived['actual_mm_s']:.6g}"+' mm/s；精确配置网格 '+str(derived['minimum_step_mm'])+' mm（非实测精度）。\n打开其中 firmware/MDK-ARM 工程，按说明编译下载。')
        except Exception as e:messagebox.showerror('未生成',str(e))

    def collect(self):
        if self.prepared is None:return messagebox.showinfo('先生成工程','请先生成、编译和烧录对应工程。')
        command=[sys.executable,str(ROOT/'tools/collect_motion.py'),'--project',str(self.prepared)]
        options={'creationflags':subprocess.CREATE_NEW_CONSOLE} if sys.platform=='win32' else {}
        subprocess.Popen(command,cwd=self.prepared,**options)

def main():
    p=argparse.ArgumentParser();p.add_argument('profile',nargs='?',type=Path,default=ROOT/'labs/01_scan_modes/settings.json');args=p.parse_args()
    profile=json.loads(args.profile.read_text(encoding='utf-8-sig'))
    window=tk.Tk()
    if 'sweep' in profile:
        from stage_panel import StagePanel
        StagePanel(window,profile)
    else:App(window,profile)
    window.mainloop()

if __name__=='__main__':main()
