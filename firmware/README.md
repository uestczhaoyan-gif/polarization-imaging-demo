# 固件工程说明

本目录包含 STM32F103C8T6 双轴扫描固件。首次使用从 `MDK-ARM/01_COMM_CHECK_NO_MOVE.uvprojx` 开始。

## 开发环境

以下版本来自工程配置文件，是复现项目时的环境依据；本次整理未运行 Keil 编译。

| 组件 | 配置记录 |
|---|---|
| IDE / 工程格式 | Keil MDK-ARM、µVision 5 |
| C 编译器 | Arm Compiler 5.06 update 7（build 960）；工程 `uAC6=0` |
| 设备包 | `Keil.STM32F1xx_DFP.2.0.0` |
| RTE 元数据 | `ARM.CMSIS.4.5.0`，CMSIS CORE 4.3.0 |
| STM32CubeMX | 6.17.0 |
| STM32CubeF1 | 1.8.7；HAL 与所需 CMSIS 文件已随仓库提供 |
| 主控与时钟 | STM32F103C8T6，8 MHz 外部晶振，PLL 至 72 MHz |
| Flash / RAM | 64 KB / 20 KB |

打开工程后，如果提示缺少设备包，通过 Pack Installer 安装对应包。若缺少 Compiler 5，在本机 Keil 中配置相应编译器，再选择工程记录的版本。将工程切换至 Compiler 6 属于工具链迁移，需要单独编译验证。

## 编译与下载

1. 打开所需 `.uvprojx`，进入 **Options for Target**，确认 Device 和编译器版本。
2. 选择 **Rebuild all target files**。检查 Build Output 中的错误和警告，确认 `0 Error(s)`。
3. 在 **Debug** 设置页选择 **CMSIS-DAP Debugger**，进入 **Settings**，Port 选择 **SW**。
4. 在 **Utilities** 设置页使用相同下载器，进入 Flash Download 设置，确认 STM32F10x 对应片内 Flash 算法。
5. 关闭电机动力电源，保持控制板 USB 与 DAP 连接，点击 **Download**，确认下载完成。
6. 检查起点与剩余行程，接通电机动力电源，等待驱动器就绪后按控制板 RESET。运动工程在通信检查后倒计时 5 秒并运行一次；通信工程检查通过后红灯常亮。

本机的下载器选择与窗口设置可能保存为 `.uvoptx` 等个人配置，这些文件由 `.gitignore` 排除。

## 工程与输出文件

| 工程 | `SCAN_STAGE` | 编译输出目录（相对 `MDK-ARM/`） |
|---|---:|---|
| `01_COMM_CHECK_NO_MOVE.uvprojx` | 0 | `Build_01_COMM_CHECK/` |
| `02_1MM_MOTION_TEST.uvprojx` | 1 | `Build_02_1MM_TEST/` |
| `03_10MM_MOTION_TEST.uvprojx` | 2 | `Build_03_10MM_TEST/` |
| `04_ACTUAL_SNAKE_RUN.uvprojx` | 3 | `Build_04_ACTUAL_RUN/` |

各工程已启用 HEX 输出，文件名与工程名一致。输出目录由 Git 忽略；需要提供预编译固件时，将经过实机验证的 HEX 作为 GitHub Release 附件，并附上对应参数与源码版本。

## 代码阅读入口

| 文件 | 用途 |
|---|---|
| [Core/Inc/snake_scan_config.h](Core/Inc/snake_scan_config.h) | 用户参数、四阶段选择、脉冲/RPM/超时换算、编译检查 |
| [Core/Src/main.c](Core/Src/main.c) | 启动、轴查询、相对位移、到位轮询、蛇形扫描与错误灯 |
| [Core/Src/usart.c](Core/Src/usart.c) | USART1 与 DMA、空闲帧接收 |
| [Core/Src/gpio.c](Core/Src/gpio.c) | PA1 状态灯初始化 |
| [BSP/Emm_V5.c](BSP/Emm_V5.c) | 厂商协议命令封装 |
| [XY_Stage_Controller.ioc](XY_Stage_Controller.ioc) | CubeMX 硬件配置参考 |

`main()` 初始化外设并检查两轴；运动阶段调用 `SnakeScan()`，逐条交替执行 X 位移和 Y 步进；正常完成后亮灯并停留。`Scan_MoveRelative()` 发送相对运动命令，读取应答并轮询到位标志；`Scan_Fail()` 尝试广播停止并持续显示错误码。状态查询带重试，运动位移命令没有自动重复发送，避免重复位移。

修改扫描范围或速度只需编辑配置头文件。当前使用仓库中的四个 Keil 工程编译；若修改 `.ioc` 并重新生成代码，请先在副本中操作，逐项对照生成差异。CubeMX 的单工程配置不包含这四个阶段的全部自定义工程设置。

完整操作见[硬件接线与首次运行](../docs/hardware/硬件接线与首次运行.md)；范围与方向见[参数与扫描路径](../docs/hardware/参数与扫描路径.md)。
