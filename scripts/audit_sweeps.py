"""Compare actual C sweep execution against the generated measurement plan."""
from pathlib import Path
import copy
import json
import subprocess
import sys
import tempfile
from audit_motion import ROOT,function
sys.path.insert(0,str(ROOT/'tools'))
from prepare_lab import configuration

def main():
    source=(ROOT/'firmware/Core/Src/main.c').read_text(encoding='utf-8-sig')
    stub=(ROOT/'scripts/sweep_path_stub.c').read_text()
    with tempfile.TemporaryDirectory() as temp:
        file=Path(temp)/'test.c';binary=Path(temp)/'test'
        for preset in (ROOT/'labs/03_stage_characterization/presets').glob('*.json'):
            original=json.loads(preset.read_text(encoding='utf-8'))
            for axis in (0,1):
                for direction in (0,1):
                    profile=copy.deepcopy(original);profile['lab']['LAB_TEST_AXIS']=axis
                    profile['scan'].update(X_FIRST_PASS_DIRECTION=direction,Y_STEP_DIRECTION=direction)
                    header,lab,record=configuration(profile)
                    expected='static const Expected expected[] = {\n'+',\n'.join('{%d,%d,%d,%d}'%(r['stage'],r['pulses'],r['rpm'],r['phase']=='return') for r in record['sweep']['plan'])+'\n};'
                    code=stub.replace('/* CONFIG */',header.decode('utf-8-sig')+'\n'+lab+'\n'+record['_sweep_header'])
                    code=code.replace('/* EXPECTED */',expected).replace('/* CODE */',function(source,'Lab_SweepDwell')+'\n'+function(source,'Lab_SweepTest'))
                    file.write_text(code,encoding='utf-8')
                    subprocess.run(['gcc','-std=c99','-Wall','-Wextra',str(file),'-o',str(binary)],check=True)
                    subprocess.run([str(binary)],check=True)

if __name__=='__main__':main()
