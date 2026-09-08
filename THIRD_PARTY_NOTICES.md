# 第三方组件说明

根目录 MIT License 沿用于本项目自行编写的扫描逻辑、配置修改与文档。第三方代码与原有版权声明保留，其授权范围按原始文件说明区分。

| 内容 | 路径 | 来源与许可说明 |
|---|---|---|
| STM32 HAL | `firmware/Drivers/STM32F1xx_HAL_Driver/` | STMicroelectronics；见目录内 `LICENSE.txt` |
| Arm CMSIS | `firmware/Drivers/CMSIS/` | Arm；见目录内 `LICENSE.txt` |
| STM32F1 CMSIS Device | `firmware/Drivers/CMSIS/Device/ST/STM32F1xx/` | STMicroelectronics；见目录内 `LICENSE.txt` |
| CubeMX 生成框架、启动文件 | `firmware/Core/`、`firmware/MDK-ARM/startup_stm32f103xb.s` | 保留各文件原有版权与授权声明；项目新增逻辑按根目录说明区分 |
| ZDT Emm V5 协议函数 | `firmware/BSP/Emm_V5.c`、`Emm_V5.h` | 张大头厂商例程；保留来源注释，未重新声明为 MIT |

ZDT 例程随本地资料提供，但本地副本中未发现明确的独立开源许可证。公开发布前需确认该部分的公开再分发条件，并将得到的授权说明补充到这里。这是现有来源记录中的待确认项。

厂商 PDF、硬件图纸、原始例程压缩包及接线图片未纳入本发布目录。获取入口见[资料来源](docs/资料来源.md)。
