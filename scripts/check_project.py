"""检查统一项目路径、文档链接和已发布结果；不替代 Keil/硬件验证。"""
from pathlib import Path
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'reconstruction'))


def main():
    projects=list((ROOT/'firmware/MDK-ARM').glob('*.uvprojx'))
    assert len(projects)==4
    for project in projects:
        tree=ET.parse(project)
        for item in tree.findall('.//FilePath'):
            assert (project.parent/item.text.replace('\\','/')).is_file(),(project,item.text)
        for item in tree.findall('.//IncludePath'):
            for name in (item.text or '').split(';'):
                if name:assert (project.parent/name.replace('\\','/')).is_dir(),name
    count=0
    for folder in [ROOT,ROOT/'docs',ROOT/'firmware',ROOT/'reconstruction',ROOT/'experiments',ROOT/'tools']:
        docs=folder.glob('*.md') if folder==ROOT else folder.rglob('*.md')
        for p in docs:
            if any(part in ('outputs','.git','.mpl-cache','Drivers') for part in p.relative_to(ROOT).parts):continue
            text=p.read_text(encoding='utf-8-sig')
            assert text.count('```')%2==0,p
            for link in re.findall(r'\]\(([^)]+)\)',text):
                if '://' in link or link.startswith('#'):continue
                assert (p.parent/link.split('#')[0]).exists(),(p,link)
                count+=1
    results=ROOT/'experiments'
    for line in (results/'manifest.sha256').read_text().splitlines():
        digest,name=line.split('  ',1)
        assert hashlib.sha256((results/name).read_bytes()).hexdigest()==digest,name
    for case in ['tape-z','tape-frame','synthetic']:
        folder=results/case
        for name in ['config.json','config-constant-period.json']:
            path=folder/name
            if not path.exists():continue
            cfg=json.loads(path.read_text(encoding='utf-8'))
            for key in ['input_file','row_windows_csv']:
                if cfg.get(key):assert (folder/cfg[key]).is_file(),(path,key)
            assert (folder/cfg['output_dir']).resolve().is_relative_to(ROOT/'local')
    photo=json.loads((results/'tape-frame/experiment.json').read_text(encoding='utf-8'))['photo']
    assert hashlib.sha256((results/'tape-frame'/photo['file']).read_bytes()).hexdigest()==photo['sha256']
    print(f'PASS: 4 Keil projects, {count} local Markdown links, result hashes, photo and runnable example paths. Firmware build/hardware tests not run.')


if __name__=='__main__':main()
