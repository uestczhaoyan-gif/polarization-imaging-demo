"""统一桌面入口：STM32 参数编辑与实验结果导航。运行 python tools/control_panel.py。"""
import difflib
from decimal import Decimal
from pathlib import Path
import os
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText
import webbrowser
from config_model import FIELDS, MM_DISPLAY_KEYS, parse_form, read_values, render, save_header, validate

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / 'firmware/Core/Inc/snake_scan_config.h'


def open_path(relative):
    path = ROOT / relative
    if not path.exists():
        messagebox.showerror('文件不存在', str(path))
        return
    if os.name == 'nt' and path.suffix != '.html':
        os.startfile(path)
    else:
        webbrowser.open(path.resolve().as_uri())


class ControlPanel(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=18)
        self.pack(fill='both', expand=True)
        self.variables = {}
        self.original = b''
        ttk.Label(self, text='偏振成像演示 · 项目工作台', font=('Microsoft YaHei UI', 20, 'bold')).pack(anchor='w')
        ttk.Label(self, text='填写扫描参数 → 预览修改 → 保存 → Keil 编译下载', padding=(0, 6, 0, 16)).pack(anchor='w')
        tabs = ttk.Notebook(self)
        tabs.pack(fill='both', expand=True)
        config = ttk.Frame(tabs, padding=12)
        examples = ttk.Frame(tabs, padding=18)
        tabs.add(config, text='  STM32 参数  ')
        tabs.add(examples, text='  实验与使用指南  ')
        self.make_config(config)
        self.make_examples(examples)
        self.reload()

    def make_config(self, page):
        left, right = ttk.Frame(page), ttk.Frame(page)
        left.pack(side='left', fill='y', padx=(0, 20))
        right.pack(side='left', fill='both', expand=True)
        groups = ttk.Notebook(left)
        groups.pack(fill='both', expand=True)
        for group in ('扫描参数', '硬件参数'):
            frame = ttk.Frame(groups, padding=10)
            groups.add(frame, text=group)
            fields = [f for f in FIELDS if f.group == group]
            for row, field in enumerate(fields):
                ttk.Label(frame, text=field.label).grid(row=row*2, column=0, sticky='w', pady=(8, 2))
                variable = tk.StringVar()
                self.variables[field.key] = variable
                if field.maximum == 1:
                    entry = ttk.Combobox(frame, textvariable=variable, values=['0', '1'], state='readonly', width=32)
                else:
                    entry = ttk.Entry(frame, textvariable=variable, width=35)
                entry.grid(row=row*2+1, column=0, sticky='ew')
                variable.trace_add('write', lambda *_: self.invalidate())
        ttk.Label(left, text='X 返程方向自动取相反值。\n方向值不能直接等同于样品的左右/上下。\n硬件参数必须与实物和驱动器设置一致。', wraplength=310, padding=(5, 10)).pack(anchor='w')
        self.summary = tk.StringVar(value='')
        ttk.Label(right, textvariable=self.summary, wraplength=550, justify='left').pack(anchor='w', pady=(0, 10))
        ttk.Label(right, text='本次修改预览（− 原值，+ 新值）').pack(anchor='w')
        self.preview = ScrolledText(right, height=16, width=66, font=('Consolas', 10), wrap='none', state='disabled')
        self.preview.pack(fill='both', expand=True, pady=8)
        buttons = ttk.Frame(right)
        buttons.pack(fill='x')
        ttk.Button(buttons, text='重新读取', command=self.reload_clicked).pack(side='left')
        ttk.Button(buttons, text='检查并预览', command=self.check).pack(side='left', padx=8)
        self.save_button = ttk.Button(buttons, text='保存到 STM32 参数文件', command=self.save, state='disabled')
        self.save_button.pack(side='left')
        ttk.Label(right, text='保存会备份原文件，并在 local/firmware-config/ 记录参数。\n然后打开相应 Keil 工程，重新编译并下载。界面不连接电机。', wraplength=550, padding=(0, 12)).pack(anchor='w')
        ttk.Button(right, text='打开 Keil 工程目录', command=lambda: open_path('firmware/MDK-ARM')).pack(anchor='w')
        self.status = tk.StringVar()
        ttk.Label(right, textvariable=self.status, wraplength=550, padding=(0, 10)).pack(anchor='w')

    def invalidate(self):
        if hasattr(self, 'save_button'):
            self.save_button.config(state='disabled')
            self.summary.set('参数有改动，请点击“检查并预览”。')

    def reload_clicked(self):
        if self.original and any(self.variables[f.key].get() != self.form_value(f.key, read_values(self.original)[f.key]) for f in FIELDS):
            if not messagebox.askyesno('重新读取', '放弃界面中尚未保存的输入，重新读取文件？'):
                return
        self.reload()

    @staticmethod
    def form_value(key, value):
        return str(Decimal(value) / 1000) if key in MM_DISPLAY_KEYS else str(value)

    def reload(self):
        try:
            self.original = HEADER.read_bytes()
            values = read_values(self.original)
            for field in FIELDS:
                self.variables[field.key].set(self.form_value(field.key, values[field.key]))
            self.status.set('已读取 firmware/Core/Inc/snake_scan_config.h')
            self.check()
        except (OSError, ValueError) as error:
            messagebox.showerror('读取失败', str(error))

    def check(self):
        try:
            values = parse_form({key: variable.get() for key, variable in self.variables.items()})
            new = render(self.original, values)
            info = validate(values)
            diff = ''.join(difflib.unified_diff(self.original.decode('utf-8-sig').splitlines(True),
                                              new.decode('utf-8-sig').splitlines(True), fromfile='当前文件', tofile='拟保存文件', n=1))
            self.preview.config(state='normal')
            self.preview.delete('1.0', 'end')
            self.preview.insert('1.0', diff or '参数与当前文件相同。')
            self.preview.config(state='disabled')
            self.summary.set(f"正式扫描：{info['rows']} 行；最后横扫 Y={info['last_line_y_mm']} mm，末尾步进到 {info['final_y_mm']} mm。\n"
                             f"X 每次 {info['x_pulses']} 脉冲；Y 每次 {info['y_pulses']} 脉冲；可设距离增量 {info['minimum_step_mm']:g} mm。\n"
                             f"命令转速 {info['rpm']} RPM；换算速度 {info['actual_mm_s']:.4g} mm/s。\n"
                             f"仅匀速运动约 {info['ideal_motion_seconds']/60:.2f} 分钟，另加启动、通信、换轴与加减速时间。\n"
                             '1 mm / 10 mm 测试工程使用各自固定范围；这里预览的是正式扫描。')
            self.save_button.config(state='normal' if new != self.original else 'disabled')
            return values
        except (ValueError, OSError) as error:
            self.save_button.config(state='disabled')
            self.summary.set('参数未通过检查：' + str(error))
            return None

    def save(self):
        values = self.check()
        if values is None:
            return
        try:
            backup = save_header(HEADER, self.original, values, ROOT / 'local/firmware-config')
            self.reload()
            if backup:
                self.status.set('已保存并备份：' + backup.name + '\n下一步：Keil Rebuild → Download。尚未烧录。')
        except (ValueError, OSError) as error:
            self.save_button.config(state='disabled')
            messagebox.showerror('未保存', str(error))

    def make_examples(self, page):
        ttk.Label(page, text='两个实测案例分别保存原始数据、参数、说明和完整结果。', font=('Microsoft YaHei UI', 12)).pack(anchor='w', pady=(0, 18))
        for title, folder, viewer in [('胶带 Z 字母 · 环境光测量', 'tape-z', 'results/viewer.html'),
                                      ('矩形胶带框 · 暗环境测量', 'tape-frame', 'results/anchored/viewer.html'),
                                      ('合成数据 · 已知答案验证', 'synthetic', 'results/viewer.html')]:
            box = ttk.LabelFrame(page, text=title, padding=14)
            box.pack(fill='x', pady=7)
            ttk.Button(box, text='打开交互结果', command=lambda p=f'experiments/{folder}/{viewer}': open_path(p)).pack(side='left')
            ttk.Button(box, text='打开案例文件夹', command=lambda p=f'experiments/{folder}': open_path(p)).pack(side='left', padx=10)
        for text, path in [('测量记录清单', 'docs/reconstruction/measurement.md'),
                           ('参数界面使用说明', 'docs/hardware/configuration-ui.md'),
                           ('重构核心处理', 'docs/reconstruction/core-process.md'),
                           ('完整文档目录', 'docs/README.md')]:
            ttk.Button(page, text=text, command=lambda p=path: open_path(p)).pack(anchor='w', pady=7)


def main():
    root = tk.Tk()
    root.title('偏振成像演示 · 参数与实验')
    root.geometry('1080x820')
    root.minsize(980, 740)
    style = ttk.Style(root)
    if 'vista' in style.theme_names():
        style.theme_use('vista')
    style.configure('.', font=('Microsoft YaHei UI', 10))
    ControlPanel(root)
    root.mainloop()


if __name__ == '__main__':
    main()
