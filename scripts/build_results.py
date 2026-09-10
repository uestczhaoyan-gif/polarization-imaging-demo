"""维护者命令：重建各实验 results/ 并更新 experiments/manifest.sha256。"""
from pathlib import Path
import hashlib
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'reconstruction'))
from snake_scan.pipeline import reconstruct
from snake_scan.report import write_outputs


def run(relative, *args):
    subprocess.run([sys.executable,str(ROOT/relative),*map(str,args)],check=True,cwd=ROOT)


def main():
    experiments=ROOT/'experiments'
    for name in ['tape-z','synthetic']:
        data=reconstruct(experiments/name/'config.json')
        write_outputs(data,experiments/name/'results')
    run('experiments/tape-z/analyze.py')
    shutil.copy2(ROOT/'local/reconstruction/tape-z/analysis.json',experiments/'tape-z/results/analysis.json')
    case=experiments/'tape-frame'
    run('experiments/tape-frame/prepare_windows.py')
    for config in ['config.json','config-constant-period.json']:
        run('reconstruction/simple_reconstruct.py','--config',case/config)
    run('experiments/tape-frame/analysis_figures.py')
    shutil.copytree(ROOT/'local/reconstruction/tape-frame',case/'results',dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('.mpl-cache','__pycache__'))
    files=sorted(p for name in ['tape-z','tape-frame','synthetic']
                 for p in (experiments/name/'results').rglob('*')
                 if p.is_file() and '.mpl-cache' not in p.parts)
    lines=[hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(experiments).as_posix() for p in files]
    (experiments/'manifest.sha256').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'Saved {len(files)} result files and SHA256 manifest.')


if __name__=='__main__':main()
