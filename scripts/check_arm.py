"""Compile and link the real sources for Cortex-M3, without flashing hardware.

Uses the Keil file list and bundled GCC startup. This validates GCC builds, not
the installed Keil toolchain, hardware wiring, or mechanical performance.
"""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
LINKER='''ENTRY(Reset_Handler)
MEMORY { FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 64K
         RAM (rwx) : ORIGIN = 0x20000000, LENGTH = 20K }
_estack = ORIGIN(RAM) + LENGTH(RAM);
SECTIONS {
 .isr_vector : { KEEP(*(.isr_vector)) } > FLASH
 .text : { *(.text*) *(.rodata*) KEEP(*(.init)) KEEP(*(.fini)) } > FLASH
 .ARM.extab : { *(.ARM.extab*) } > FLASH
 .ARM.exidx : { __exidx_start = .; *(.ARM.exidx*) __exidx_end = .; } > FLASH
 .preinit_array : { __preinit_array_start = .; KEEP(*(.preinit_array*)) __preinit_array_end = .; } > FLASH
 .init_array : { __init_array_start = .; KEEP(*(.init_array*)) __init_array_end = .; } > FLASH
 .fini_array : { __fini_array_start = .; KEEP(*(.fini_array*)) __fini_array_end = .; } > FLASH
 _sidata = LOADADDR(.data);
 .data : { . = ALIGN(4); _sdata = .; *(.data*) . = ALIGN(4); _edata = .; } > RAM AT> FLASH
 .bss : { . = ALIGN(4); _sbss = .; *(.bss*) *(COMMON) . = ALIGN(4); _ebss = .; end = .; _end = .; } > RAM
 .reserved (NOLOAD) : { . = ALIGN(8); . += 2048; } > RAM
}
'''

def main():
    with tempfile.TemporaryDirectory() as temp:
        work=Path(temp);shutil.copytree(ROOT/'firmware',work/'firmware')
        project=work/'firmware/MDK-ARM/04_ACTUAL_SNAKE_RUN.uvprojx';tree=ET.parse(project)
        sources=[(project.parent/f.findtext('FilePath').replace('\\','/')).resolve()
                 for f in tree.findall('.//File') if f.findtext('FileType')=='1']
        includes=sorted({str((project.parent/p.replace('\\','/')).resolve())
                         for item in tree.findall('.//IncludePath') for p in (item.text or '').split(';') if p})
        flags=['-mcpu=cortex-m3','-mthumb','-std=c99','-Os','-ffunction-sections','-fdata-sections',
               '-DUSE_HAL_DRIVER','-DSTM32F103xB','-Wall','-Wextra','-Werror=implicit-function-declaration']
        for include in includes:flags+=['-I',include]
        lab=work/'firmware/Core/Inc/lab_config.h';original=lab.read_text()
        linker=work/'check.ld';linker.write_text(LINKER)
        startup=work/'firmware/Drivers/CMSIS/Device/ST/STM32F1xx/Source/Templates/gcc/startup_stm32f103xb.s'
        # Bare-metal C has no constructors; Newlib still references these CRT hooks.
        runtime=work/'crt_hooks.c';runtime.write_text('void _init(void) {}\nvoid _fini(void) {}\n')
        for experiment,stage in [(0,0),(0,3),(1,1),(1,3),(2,3),(3,3)]:
            text=re.sub(r'(#define LAB_EXPERIMENT\s+)\d+U',lambda m:m[1]+str(experiment)+'U',original)
            text=re.sub(r'(#define LAB_LOG_ENABLE\s+)\d+U',lambda m:m[1]+str(int(experiment!=0))+'U',text)
            lab.write_text(text)
            objects=[]
            for i,source in enumerate(sources):
                obj=work/f'{i}.o';objects.append(str(obj))
                subprocess.run(['arm-none-eabi-gcc',*flags,f'-DSCAN_STAGE={stage}','-c',str(source),'-o',str(obj)],check=True)
            startobj=work/'startup.o';objects.append(str(startobj))
            subprocess.run(['arm-none-eabi-gcc','-mcpu=cortex-m3','-mthumb','-c',str(startup),'-o',str(startobj)],check=True)
            crt=work/'crt.o';objects.append(str(crt))
            subprocess.run(['arm-none-eabi-gcc','-mcpu=cortex-m3','-mthumb','-c',str(runtime),'-o',str(crt)],check=True)
            elf=work/'firmware.elf'
            subprocess.run(['arm-none-eabi-gcc','-mcpu=cortex-m3','-mthumb','--specs=nano.specs','--specs=nosys.specs',
                            '-nostartfiles','-Wl,--gc-sections','-T',str(linker),*objects,'-o',str(elf)],check=True)
            print(f'PASS: Cortex-M3 link experiment={experiment} stage={stage}, 64K FLASH / 20K RAM with 2K reserve',flush=True)
            subprocess.run(['arm-none-eabi-size',str(elf)],check=True)

if __name__=='__main__':main()
