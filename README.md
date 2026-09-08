# STM32 双轴平移台扫描控制器

**STM32 ZDT XY Stage Controller** · `stm32-zdt-xy-stage`

用于偏振成像演示实验的双轴平移台控制项目。STM32F103C8T6 通过串口与 ZDT X42S 第二代闭环步进电机通信，驱动水平、垂直两条丝杆滑台完成矩形区域的蛇形扫描。

本仓库提供平移台固件、接线说明和参数修改方法，供使用相同设备的同学复现和扩展。相机采集、偏振器控制与图像重建需要由成像系统另行实现；当前固件没有相机触发或采集同步接口。

## 从这里开始

| 你要做什么 | 阅读入口 |
|---|---|
| 第一次接线、编译和运行 | [硬件接线与首次运行](docs/硬件接线与首次运行.md) |
| 更换掩模版、调整范围、方向或速度 | [参数与扫描路径](docs/参数与扫描路径.md) |
| 查找代码入口、了解四个工程 | [固件说明](firmware/README.md) |
| 状态灯报错、下载失败或距离异常 | [常见问题](docs/常见问题.md) |
| 将这个项目上传到 GitHub | [GitHub 上传指南](docs/GitHub上传指南.md) |
| 查找厂商手册和第三方组件来源 | [资料来源](docs/资料来源.md) |

## 硬件与默认参数

以下是本项目的目标配置；更换硬件时请逐项核对。

| 项目 | 配置 |
|---|---|
| 控制板 | 野火小智 STM32F103C8T6 双 USB 款 |
| 下载器 | 野火 DAP 小智款，SWD 接口 |
| 电机 | ZDT X42S 第二代闭环步进电机，兼容 Emm V5 命令 |
| 通信 | USART1，PA9 / PA10，115200、8N1；按接口版本使用 TTL 或 RS485 |
| 轴地址 | 水平 X = 2，垂直 Y = 1 |
| 电机与丝杆 | 1.8°、16 细分、T6×1，导程 1 mm/圈 |
| 默认扫描 | 宽 100 mm、高 100 mm、行距 2 mm、速度 1 mm/s |
| 状态灯 | PA1 红灯，低电平点亮 |

**程序使用 Emm V5 命令协议。** RS485 是通信接口形式；驱动器需要运行与此命令兼容的固件。仅支持 Modbus 的固件不能直接使用本项目。

## 快速运行

1. 按[首次运行说明](docs/硬件接线与首次运行.md)核对接线、地址、细分和电源。
2. 使用 Keil MDK 打开 `firmware/MDK-ARM/01_COMM_CHECK_NO_MOVE.uvprojx`，重新编译并下载。电机上电后复位控制板，红灯常亮表示两轴通信检查通过。
3. 依次运行 1 mm 和 10 mm 测试，检查运动方向、实际位移和换轴顺序。
4. 在 [snake_scan_config.h](firmware/Core/Inc/snake_scan_config.h) 中设置扫描参数。
5. 将两轴放在扫描起点，编译并下载正式工程。复位后，程序检查通信、闪灯倒计时 5 秒，再执行一次扫描。

| 顺序 | Keil 工程（位于 `firmware/MDK-ARM/`） | 运动范围 |
|---:|---|---|
| 1 | `01_COMM_CHECK_NO_MOVE.uvprojx` | 只查询两轴状态 |
| 2 | `02_1MM_MOTION_TEST.uvprojx` | X 往返各 1 mm；Y 累计 2 mm |
| 3 | `03_10MM_MOTION_TEST.uvprojx` | X 往返各 10 mm；Y 累计 4 mm |
| 4 | `04_ACTUAL_SNAKE_RUN.uvprojx` | 使用配置文件中的扫描范围 |

四个工程共用同一套源码，通过 `SCAN_STAGE` 编译宏选择阶段。每次切换工程或修改参数后都重新编译、下载。

## 设置扫描范围

日常参数集中在 `firmware/Core/Inc/snake_scan_config.h` 顶部：

```c
#define MASK_SCAN_WIDTH_MM       100UL  // 每条水平线长，mm
#define MASK_SCAN_HEIGHT_MM      100UL  // 垂直累计位移，mm
#define SCAN_LINE_STEP_MM          2UL  // 每条水平线后的垂直步进，mm
#define SCAN_SPEED_UM_PER_SEC   1000UL  // 两轴线速度，um/s
```

水平线数 = 高度 ÷ 行距。高度必须是行距的整数倍；宽度、高度和行距使用正整数毫米。

| 宽 × 高 | 行距 | 水平线数 | 1 mm/s 下的理想运动时间 |
|---|---:|---:|---:|
| 100 × 100 mm | 2 mm | 50 | 85 分钟 |
| 100 × 50 mm | 2 mm | 25 | 42.5 分钟 |
| 50 × 100 mm | 2 mm | 50 | 43.3 分钟 |

每条水平线完成后，Y 轴沿配置方向移动一次行距，包括最后一条。以 100 × 100 mm、行距 2 mm 为例：水平线位于相对 Y = 0、2、…、98 mm，最后停在 Y = 100 mm，Y = 100 mm 处不再扫描水平线。方向和终点详见[参数与扫描路径](docs/参数与扫描路径.md)。

## 项目结构

```text
stm32-zdt-xy-stage/
├── firmware/
│   ├── Core/                  扫描逻辑、参数、外设初始化
│   ├── BSP/                   ZDT Emm V5 协议函数
│   ├── Drivers/               ST HAL 与 CMSIS 依赖及原始许可证
│   ├── MDK-ARM/               四个 Keil 工程与启动文件
│   ├── XY_Stage_Controller.ioc  CubeMX 硬件配置
│   └── README.md              固件入口与编译环境
├── docs/                      接线、参数、排错、资料与上传指南
├── .gitignore                 编译产物与本地资料排除规则
├── .gitattributes             文本换行规则
├── LICENSE
├── THIRD_PARTY_NOTICES.md
├── CONTRIBUTING.md
└── CHANGELOG.md
```

## 运行边界

运动程序在上电或复位后自动启动一次。下载时关闭电机动力电源；运行前确认两轴沿配置方向留有足够行程。程序没有机械回零、硬件限位输入或急停输入，重新扫描前需要恢复起点。通信故障时会尝试广播停止，但通信中断时不能保证停止命令送达，应保留可直接切断电机动力的开关。

本次整理完成文件与工程引用的静态检查，编译及实机验证状态见[验证记录](docs/验证记录.md)。

## 许可证与参与方式

本项目自行编写的扫描逻辑、参数配置修改和说明文档沿用 MIT License。ST、Arm 与 ZDT 文件的来源和许可范围见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。提交问题或改进前，请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。
