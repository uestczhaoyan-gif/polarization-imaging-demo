"""Export one complete tracked project and three standalone lab source packages."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from prepare_lab import prepare

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--version',required=True)
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip():raise ValueError('Commit changes before packaging')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    prefix='polarization-imaging-demo-'+args.version
    complete=out/(prefix+'-complete.zip')
    subprocess.run(['git','archive','--format=zip','--prefix='+prefix+'/',f'--output={complete}','HEAD'],cwd=ROOT,check=True)
    with zipfile.ZipFile(complete) as z:
        assert z.testzip() is None;z.extractall(out)
    exported=out/prefix
    for profile_path in sorted((exported/'labs').glob('*/settings.json')):
        name=profile_path.parent.name;profile=json.loads(profile_path.read_text(encoding='utf-8'))
        folder=prepare(profile,out/name,root=exported)
        (folder/'SOURCE_REVISION.txt').write_text(commit+'\n',encoding='ascii')
        archive=out/(name+'-'+args.version+'.zip')
        with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
            for file in sorted(folder.rglob('*')):
                if file.is_file():z.write(file,file.relative_to(out))
        with zipfile.ZipFile(archive) as z:assert z.testzip() is None
        # Header digests match the generated configuration record.
        config=json.loads((folder/'prepared-config.json').read_text(encoding='utf-8'))
        for name,digest in config['headers_sha256'].items():
            assert hashlib.sha256((folder/'firmware/Core/Inc'/name).read_bytes()).hexdigest()==digest
    sums=[]
    for archive in sorted(out.glob('*.zip')):
        digest=hashlib.sha256(archive.read_bytes()).hexdigest();sums.append(digest+'  '+archive.name)
    (out/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n',encoding='ascii')
    (out/'交付说明.md').write_text('# '+args.version+' 实验包\n\n代码提交：`'+commit+'`\n\n完整项目：'+prefix+'。三个数字开头的目录可独立编译；各有 START.cmd 和 README.md。\n\n先读任意实验包的 labs/README.md。实验二及其他主动开启日志的配置需要外接 3.3V USB-TTL（PB10→RX、PB11←TX、GND），并安装 pyserial。\n\n所有包是源代码；没有伪称已烧录的 HEX，也没有生成虚假的实测结果。精度与最高平稳速度需按说明测量。\n',encoding='utf-8')
    print(out)

if __name__=='__main__':main()
