"""Prepare an independent, unflashed Keil project from a small JSON profile."""
import argparse
import json
from pathlib import Path
import shutil
from config_model import read_values, render, validate, pattern
from lab_common import fresh_directory, write_json, sha

ROOT = Path(__file__).resolve().parents[1]
LAB_DEFAULTS = dict(LAB_EXPERIMENT=0, LAB_LOG_ENABLE=0, LAB_TEST_AXIS=0,
                    LAB_TEST_DISTANCE_UM=1000, LAB_TEST_REPEATS=3, LAB_TEST_DWELL_MS=1000)

def configuration(profile, root=ROOT):
    source=(root/'firmware/Core/Inc/snake_scan_config.h').read_bytes()
    values=read_values(source)
    for key,value in profile.get('scan',{}).items():
        if key not in values:raise ValueError('Unknown scan parameter: '+key)
        if type(value) is not int:raise ValueError(key+' must be an integer in firmware units')
        values[key]=value
    values['X_ALTERNATE_PASS_DIRECTION']=1-values['X_FIRST_PASS_DIRECTION']
    derived=validate(values)
    lab=dict(LAB_DEFAULTS)
    for key,value in profile.get('lab',{}).items():
        if key not in lab or type(value) is not int:raise ValueError('Invalid lab parameter: '+key)
        lab[key]=value
    if lab['LAB_EXPERIMENT'] not in range(4) or lab['LAB_LOG_ENABLE'] not in (0,1) or lab['LAB_TEST_AXIS'] not in (0,1):
        raise ValueError('Invalid experiment, logging or axis')
    if lab['LAB_EXPERIMENT'] and not lab['LAB_LOG_ENABLE']:raise ValueError('Experiments 1–3 require logging and PC start')
    n=lab['LAB_TEST_REPEATS'];d=lab['LAB_TEST_DISTANCE_UM']
    if not 1<=n<=1000 or not 0<=lab['LAB_TEST_DWELL_MS']<=60000:raise ValueError('Repetitions 1–1000; dwell 0–60000 ms')
    if lab['LAB_EXPERIMENT']>=2:
        total=d*(n if lab['LAB_EXPERIMENT']==3 else 1)
        safe=values['Y_AXIS_MAX_SAFE_TRAVEL_UM' if lab['LAB_TEST_AXIS'] else 'X_AXIS_MAX_SAFE_TRAVEL_UM']
        ppr=values['MOTOR_FULL_STEPS_PER_REV']*values['MOTOR_MICROSTEP'];lead=values['LEAD_UM_PER_REV']
        if d<=0 or d*ppr%lead:raise ValueError('Distance must map exactly to whole pulses')
        if total>safe or total*ppr//lead>0xffffffff:raise ValueError('Test exceeds safe travel or pulse limit')
        if total*60000/(derived['rpm']*lead)+20000>0xffffffff:raise ValueError('Timeout overflow')
    text=(root/'firmware/Core/Inc/lab_config.h').read_text(encoding='utf-8-sig')
    for k,v in lab.items():
        if len(pattern(k).findall(text))!=1:raise ValueError('Missing lab macro: '+k)
        text=pattern(k).sub(lambda m:m[1]+str(v)+m[3],text)
    return render(source,values),text,dict(scan=values,lab=lab,derived=derived,flashed=False)

def prepare(profile, output, root=ROOT):
    header,lab,record=configuration(profile,root)
    output=Path(output).resolve()
    # Reject destinations inside firmware/tools to avoid recursive copies.
    included=('.github','firmware','tools','docs','labs','reconstruction','experiments','scripts')
    for folder in included:
        if output.is_relative_to((root/folder).resolve()):raise ValueError('Choose local/lab-projects or another output directory')
    out=fresh_directory(output)
    ignore=shutil.ignore_patterns('__pycache__','*.pyc','Objects','Listings','Build_*','*.uvguix.*','*.uvoptx','build')
    for folder in included:
        if (root/folder).exists():shutil.copytree(root/folder,out/folder,ignore=ignore)
    for name in ('LICENSE','README.en.md','.gitignore','.gitattributes'):
        if (root/name).exists():shutil.copy2(root/name,out/name)
    (out/'firmware/Core/Inc/snake_scan_config.h').write_bytes(header)
    (out/'firmware/Core/Inc/lab_config.h').write_text(lab,encoding='utf-8')
    record['title']=profile.get('title','Lab project')
    record['headers_sha256']={name:sha(out/'firmware/Core/Inc'/name) for name in ('snake_scan_config.h','lab_config.h')}
    write_json(out/'prepared-config.json',record)
    write_json(out/'experiment-profile.json',profile)
    (out/'START.cmd').write_text('@echo off\ncd /d "%~dp0"\npowershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\\launch.ps1" -LabProfile "%~dp0experiment-profile.json"\npause\n',encoding='ascii')
    (out/'README.md').write_text('# '+record['title']+'\n\n先读 [实验使用说明](labs/README.md)。\n\n这是独立源代码工程，**尚未烧录、未经过你的实机验证**。\n双击 START.cmd 调整参数并生成新的副本；烧录本包使用 firmware/MDK-ARM 中的工程。\n先 01 通信检查，再 02 小行程核对方向，最后 04 执行本包实验。\n03 也是固定小行程扫描，只有 04 执行单轴测试参数。\n日志实验先启动电脑收集器，再复位开发板，收到 READY 后输入 g。\n',encoding='utf-8')
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('profile',type=Path);p.add_argument('--output',required=True,type=Path)
    args=p.parse_args();print(prepare(json.loads(args.profile.read_text(encoding='utf-8-sig')),args.output))

if __name__=='__main__':main()
