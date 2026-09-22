"""在主机上编译实际 C 函数，检查命令与故障响应；不连接电机。

依赖 Python 和 gcc。HAL/时间/驱动反馈由测试桩模拟，不是硬件仿真。
覆盖小数距离、短运动和通信故障；不能认定偶发快速横移的根因。
"""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def function(text, name):
    match = re.search(r'^(?:static )?(?:bool|void) ' + name + r'\([^;{]+\)\s*\{', text, re.M)
    if not match:
        raise ValueError(name)
    start = match.start()
    depth = 1
    end = match.end()
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def main():
    source = (ROOT/'firmware/Core/Src/main.c').read_text(encoding='utf-8-sig')
    driver = (ROOT/'firmware/BSP/Emm_V5.c').read_text(encoding='utf-8-sig')
    header = (ROOT/'firmware/BSP/Emm_V5.h').read_text(encoding='utf-8-sig')
    enum = re.search(r'typedef enum \{.*?\}SysParams_t;', header, re.S).group()
    config = (ROOT/'firmware/Core/Inc/snake_scan_config.h').read_text(encoding='utf-8-sig')
    # Only the temporary test configuration is changed; production source is untouched.
    config = re.sub(r'(#define SCAN_SPEED_UM_PER_SEC\s+)\d+UL', r'\g<1>2000UL', config)
    code = (ROOT/'scripts/motion_audit_stub.c').read_text()
    code = code.replace('/* CONFIG */', config + '\n' + enum)
    names = ['Emm_V5_Pos_Control', 'Emm_V5_Read_Sys_Params']
    code = code.replace('/* DRIVER */', '\n'.join(function(driver, n) for n in names))
    names = ['Scan_ClearRxFrame', 'Scan_TakeRxFrame', 'Scan_RestartUartRx',
             'Scan_WaitReply', 'Scan_ReadMotorStatus', 'Scan_WaitAxisReached', 'Scan_MoveRelative']
    code = code.replace('/* SCAN */', '\n'.join(function(source, n) for n in names))
    with tempfile.TemporaryDirectory() as temp:
        cfile = Path(temp)/'audit.c'
        binary = Path(temp)/'audit'
        cfile.write_text(code, encoding='utf-8')
        subprocess.run(['gcc', '-std=c99', '-Wall', '-Wextra', str(cfile), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
        # Compile all stage configurations, and reject paths that would truncate.
        for stage in range(4):
            variant=re.sub(r'(#define SCAN_LINE_STEP_UM\s+)\d+UL',r'\g<1>5UL',config)
            cfile.write_text(f'#define SCAN_STAGE {stage}U\n'+variant+'\nint main(void) { return 0; }',encoding='utf-8')
            subprocess.run(['gcc','-std=c99','-Wall','-Wextra','-fsyntax-only',str(cfile)],check=True)
        invalid=[('SCAN_LINE_STEP_UM',1),('MASK_SCAN_WIDTH_UM',100005),
                 ('MASK_SCAN_HEIGHT_UM',99999),('SCAN_SPEED_UM_PER_SEC',1)]
        for key,value in invalid:
            variant=re.sub(r'(#define '+key+r'\s+)\d+UL',lambda m:m[1]+str(value)+'UL',config)
            cfile.write_text(variant,encoding='utf-8')
            result=subprocess.run(['gcc','-std=c99','-fsyntax-only',str(cfile)],capture_output=True)
            assert result.returncode!=0,(key,value)
        print('PASS: all four stages accept 0.005 mm; subpulse, travel, row division and zero RPM are compile-time errors.')
        path_stub=(ROOT/'scripts/scan_path_stub.c').read_text()
        for mode in (0,1):
            for rows in (1,2,3):
                for direction in (0,1):
                    variant=config
                    for key,value in dict(SCAN_MODE=mode,MASK_SCAN_WIDTH_UM=500,
                                          MASK_SCAN_HEIGHT_UM=rows*100,SCAN_LINE_STEP_UM=100,
                                          X_FIRST_PASS_DIRECTION=direction,X_ALTERNATE_PASS_DIRECTION=1-direction,
                                          Y_STEP_DIRECTION=direction).items():
                        variant=re.sub(r'(#define '+key+r'\s+)\d+U(L?)',lambda m:m[1]+str(value)+'U'+m[2],variant)
                    code=path_stub.replace('/* CONFIG */','#define SCAN_STAGE 3U\n'+variant)
                    code=code.replace('/* LOOP */',function(source,'SnakeScan'))
                    cfile.write_text(code,encoding='utf-8')
                    subprocess.run(['gcc','-std=c99','-Wall','-Wextra',str(cfile),'-o',str(binary)],check=True)
                    subprocess.run([str(binary)],check=True)


if __name__ == '__main__':
    main()
