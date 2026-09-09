"""检查统一项目路径、文档链接和已发布结果；不替代 Keil/硬件验证。"""
from pathlib import Path
import hashlib
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
    for folder in [ROOT,ROOT/'docs',ROOT/'firmware',ROOT/'reconstruction']:
        docs=folder.glob('*.md') if folder==ROOT else folder.rglob('*.md')
        for p in docs:
            if any(part in ('outputs','.git','.mpl-cache','Drivers') for part in p.relative_to(ROOT).parts):continue
            text=p.read_text(encoding='utf-8-sig')
            assert text.count('```')%2==0,p
            for link in re.findall(r'\]\(([^)]+)\)',text):
                if '://' in link or link.startswith('#'):continue
                assert (p.parent/link.split('#')[0]).exists(),(p,link)
                count+=1
    results=ROOT/'reconstruction/results'
    for line in (results/'manifest.sha256').read_text().splitlines():
        digest,name=line.split('  ',1)
        assert hashlib.sha256((results/name).read_bytes()).hexdigest()==digest,name
    print(f'PASS: 4 Keil projects, {count} local Markdown links, published result hashes. Firmware build/hardware tests not run.')


if __name__=='__main__':main()
