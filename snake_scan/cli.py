"""命令行与逐项参数向导；所有实验参数最终写入 JSON，便于复现。"""
import argparse
import json
import sys
from pathlib import Path
import webbrowser
from .pipeline import reconstruct, positive
from .report import write_outputs


def template(mode):
    cfg={'input_file':'data.csv','input_format':'csv','output_dir':'outputs',
         'mode':mode,'width_mm':100,'line_step_mm':2,'columns':50,
         'threshold_uA':None,'minimum_samples_per_pixel':1,
         'reported_start_wait_seconds':None,'title':'我的蛇形扫描'}
    if mode in ('index_windows','time_windows'):
        cfg['row_windows_csv']='rows.csv'
        if mode=='time_windows':
            cfg['max_sample_gap_seconds']=None
    elif mode=='constant':
        cfg.update(samples_per_row=None,start_point=None,turnaround_fraction=0,first_row_reverse=False)
    else:
        cfg.update(row_period_search=None,fit_point_range=None,
                   alignment_median_window=31,turnaround_fraction=0,first_row_reverse=False)
    return cfg


def wizard(path):
    """不替用户猜采样率或周期。默认值仅是输入便利，输出配置可复查。"""
    def ask(prompt,default=''):
        answer=input(f'{prompt}'+(f' [{default}]' if default!='' else '')+': ').strip()
        return answer or default
    def number(prompt,default='',integer=False):
        while True:
            try:return positive(ask(prompt,default),prompt,integer)
            except ValueError as e:print(e)
    print('路径相对于将要保存的配置文件；时间窗必须来自同一时钟下的有效匀速横扫。')
    mode=ask('模式：time_windows / index_windows / constant / estimate','time_windows')
    if mode not in ('time_windows','index_windows','constant','estimate'):
        raise ValueError('未知模式。')
    cfg=template(mode)
    cfg['input_file']=ask('原始数据文件','data.csv')
    cfg['input_format']=ask('数据格式 csv / legacy','csv')
    cfg['width_mm']=number('横扫宽度 mm',100)
    cfg['line_step_mm']=number('行距 mm',2)
    cfg['columns']=number('每行像素数',50,True)
    value=ask('阈值 μA（auto 为 Otsu；需确认信号确有两类）','auto')
    cfg['threshold_uA']=None if value=='auto' else float(value)
    if mode in ('time_windows','index_windows'):
        cfg['row_windows_csv']=ask('实际行窗口文件','rows.csv')
        if mode=='time_windows':
            dt=ask('无 time_s 时填写实测固定采样间隔秒；已有 time_s 则留空')
            if dt:cfg['sample_interval_seconds']=positive(dt,'采样间隔')
    else:
        cfg['first_row_reverse']=ask('第一行是否反向 y/n','n').lower()=='y'
        cfg['turnaround_fraction']=float(ask('换行占整个周期比例（仅假设，0～0.2 之间）',0))
        if mode=='constant':
            cfg['samples_per_row']=number('每行周期采样点数')
            cfg['start_point']=float(ask('首条完整周期起点 point',0))
        else:
            print('估计依赖相邻行连续性，可能多解。此处范围须从本次信号重复周期判断。')
            cfg['row_period_search']=[number('周期搜索下限点数'),number('周期搜索上限点数')]
            cfg['fit_point_range']=[int(ask('拟合开始点',0)),number('拟合结束点（不包含）','',True)]
    cfg['output_dir']=ask('输出目录','outputs')
    write_config(path,cfg)
    print('配置已保存。先核对参数，再运行：python reconstruct.py run --config "'+str(path)+'" --open')


def write_config(path,cfg):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    # x 模式避免覆盖已有实验配置。
    with path.open('x',encoding='utf-8') as f:
        json.dump(cfg,f,ensure_ascii=False,indent=2)
        f.write('\n')


def main():
    # 英文 Windows / 重定向管道可能默认为 cp1252；中文提示也必须可输出。
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):
            stream.reconfigure(encoding='utf-8',errors='backslashreplace')
    parser=argparse.ArgumentParser(description='连续电流 → 蛇形二维图与双向交互对应表')
    sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run',help='按 JSON 配置重构')
    run.add_argument('--config',type=Path,required=True)
    run.add_argument('--open',action='store_true',help='完成后用浏览器打开离线查看器')
    run.add_argument('--overwrite',action='store_true',help='允许在已有输出目录重新生成结果')
    init=sub.add_parser('init',help='生成待填写的配置模板')
    init.add_argument('--mode',choices=['time_windows','index_windows','constant','estimate'],default='time_windows')
    init.add_argument('--output',type=Path,default=Path('config.json'))
    wiz=sub.add_parser('wizard',help='逐项询问并保存实验参数')
    wiz.add_argument('--output',type=Path,default=Path('config.json'))
    view=sub.add_parser('view',help='打开已经生成的离线查看器')
    view.add_argument('path',type=Path)
    args=parser.parse_args()
    try:
        if args.command=='init':
            write_config(args.output,template(args.mode));print('已生成待填写配置：',args.output)
        elif args.command=='wizard':wizard(args.output)
        elif args.command=='view':
            path=args.path.resolve()
            if not path.is_file():raise ValueError('查看器文件不存在。')
            webbrowser.open(path.as_uri())
        else:
            cfg=json.loads(args.config.read_text(encoding='utf-8-sig'))
            output=(args.config.resolve().parent/cfg.get('output_dir','outputs')).resolve()
            if output.exists() and any(output.iterdir()) and not args.overwrite:
                raise ValueError('输出目录非空。换新目录，或明确加 --overwrite 重新生成。')
            if cfg.get('mode')=='estimate' and (cfg.get('row_period_search') is None or cfg.get('fit_point_range') is None):
                raise ValueError('estimate 必须填写 row_period_search 和 fit_point_range。')
            data=reconstruct(args.config)
            # 原始输入不得放在可能被结果文件覆盖的位置。
            source=(args.config.resolve().parent/cfg['input_file']).resolve()
            if source.parent==output or args.config.resolve().parent==output:
                raise ValueError('请把输出放到独立目录，不要与输入数据或配置放在同一层。')
            write_outputs(data,output)
            m=data['metadata']
            print(f"完成：{m['complete_rows']} × {m['columns']} 像素；{m['points_used']} 点用于图像。")
            print('结果与交互图：',output/'viewer.html')
            for note in m['notes']:print('说明：',note)
            if args.open:webbrowser.open((output/'viewer.html').as_uri())
    except (ValueError,KeyError,TypeError,OSError) as e:
        parser.exit(2,f'无法重构：{e}\n')


if __name__=='__main__':main()
