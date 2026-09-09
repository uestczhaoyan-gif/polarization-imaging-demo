"""在主机上编译实际 C 函数，检查命令与故障响应；不连接电机。

依赖 Python 和 gcc。HAL/时间/驱动反馈由测试桩模拟，不是硬件仿真。
已知的提前到位风险用 REPRODUCED 输出，不代表修复或事发根因。
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


if __name__ == '__main__':
    main()
