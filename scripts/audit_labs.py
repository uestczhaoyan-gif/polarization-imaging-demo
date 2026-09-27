"""Compile production Lab_AxisTest using a bounded host test, no motors."""
from pathlib import Path
import re
import subprocess
import tempfile
from audit_motion import ROOT,function

def main():
    config=(ROOT/'firmware/Core/Inc/snake_scan_config.h').read_text(encoding='utf-8-sig')
    lab=(ROOT/'firmware/Core/Inc/lab_config.h').read_text()
    source=(ROOT/'firmware/Core/Src/main.c').read_text(encoding='utf-8-sig')
    stub=(ROOT/'scripts/lab_path_stub.c').read_text()
    with tempfile.TemporaryDirectory() as temp:
        file=Path(temp)/'test.c';binary=Path(temp)/'test'
        for mode in (2,3):
            for axis in (0,1):
                for direction in (0,1):
                    variant=config+'\n'+lab
                    for key,value in dict(LAB_LOG_ENABLE=1,LAB_EXPERIMENT=mode,LAB_TEST_AXIS=axis,
                                          X_FIRST_PASS_DIRECTION=direction,X_ALTERNATE_PASS_DIRECTION=1-direction,Y_STEP_DIRECTION=direction).items():
                        variant=re.sub(r'(#define '+key+r'\s+)\d+U(L?)',lambda m:m[1]+str(value)+'U'+m[2],variant)
                    code=stub.replace('/* CONFIG */',variant).replace('/* LOOP */',function(source,'Lab_AxisTest'))
                    file.write_text(code,encoding='utf-8')
                    subprocess.run(['gcc','-std=c99','-Wall','-Wextra',str(file),'-o',str(binary)],check=True)
                    subprocess.run([str(binary)],check=True)
        variant=re.sub(r'(#define LAB_LOG_ENABLE\s+)\d+U',r'\g<1>1U',lab)
        code=(ROOT/'firmware/Core/Src/lab_io.c').read_text()
        code=re.sub(r'^#include "[^\n]+"\n','',code,flags=re.M)
        # Function declarations are normally supplied by lab_io.h.
        declarations=(ROOT/'firmware/Core/Inc/lab_io.h').read_text()
        logger=(ROOT/'scripts/lab_io_stub.c').read_text().replace('/* CONFIG */',config+'\n'+variant+'\n'+declarations)
        logger=logger.replace('/* CODE */',code)
        file.write_text(logger,encoding='utf-8')
        subprocess.run(['gcc','-std=c99','-Wall','-Wextra',str(file),'-o',str(binary)],check=True)
        for scenario in ('start','queue','tx','ore'):subprocess.run([str(binary),scenario],check=True)

if __name__=='__main__':main()
