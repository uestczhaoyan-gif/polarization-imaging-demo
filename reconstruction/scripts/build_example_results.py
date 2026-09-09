"""维护者命令：重建并校验随仓库发布的完整结果快照。"""
from pathlib import Path
import hashlib
import importlib.util
import shutil
import sys
import subprocess

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from snake_scan.pipeline import reconstruct
from snake_scan.report import write_outputs


def main():
    for name in ['z_tape','synthetic']:
        data=reconstruct(ROOT/'examples'/name/'config.json')
        write_outputs(data,ROOT/'results'/name)
    path=ROOT/'examples/z_tape/analyze.py'
    spec=importlib.util.spec_from_file_location('case_analysis',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.main()
    shutil.copy2(ROOT/'outputs/z_tape/analysis.json',ROOT/'results/z_tape/analysis.json')
    case=ROOT/'examples/dark_80mm_20260909'
    subprocess.run([sys.executable,str(case/'prepare_windows.py')],check=True)
    for config in ['simple.json','uniform.json']:
        subprocess.run([sys.executable,str(ROOT/'simple_reconstruct.py'),'--config',str(case/config)],check=True)
    subprocess.run([sys.executable,str(case/'analysis_figures.py')],check=True)
    shutil.copytree(ROOT/'outputs/dark_80mm_20260909',ROOT/'results/dark_80mm_20260909',
                    dirs_exist_ok=True,ignore=shutil.ignore_patterns('.mpl-cache','__pycache__'))
    # 缓存不是结果文件；校验清单采用相对路径便于下载后验证。
    folder=ROOT/'results'
    files=sorted(p for sub in ['z_tape','synthetic','dark_80mm_20260909'] for p in (folder/sub).rglob('*')
                 if p.is_file() and '.mpl-cache' not in p.parts)
    lines=[hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(folder).as_posix() for p in files]
    (folder/'manifest.sha256').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'Saved {len(files)} result files and SHA256 manifest.')


if __name__=='__main__':main()
