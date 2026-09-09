# 偏振成像演示：双轴扫描与电流图像重构

**中文** | [English](README.en.md)

一个完整的成像演示工程：STM32F103 控制 ZDT 双轴平移台进行蛇形扫描，源表记录光电流，Python 将连续采样重排为二维图，并提供像素与原始曲线双向对应的离线交互图。

本项目将原来的平移台控制和重构例程合并维护，保留两部分 Git 历史、实测数据与全部结果。**目前实现的是单通道电流空间成像**；源表采集仍由仪器软件完成，尚未实现电机与源表的自动同步触发，也不计算 Stokes 参数、偏振度或偏振角。

![Z 胶带实测重构](reconstruction/examples/z_tape/reference/02_reconstruction.png)

## 第一次打开

下载 [完整项目包](https://github.com/uestczhaoyan-gif/polarization-imaging-demo/releases/latest)，或在仓库页面选择 Code → Download ZIP，解压后：

1. **先看结果**：双击根目录 `open_results.cmd`，或用浏览器打开 `reconstruction/results/z_tape/viewer.html`。不需要 Python、不需要联网。
2. **理解对应关系**：点击二维像素查看对应行和全部原始采样；点击曲线可反查像素。[阅读指南](reconstruction/docs/reading-guide.md)。
3. **准备新实验**：先读 [测量记录清单](reconstruction/docs/measurement.md)，保存时间戳、逐行运动记录和仪器参数。
4. **连接和运行平移台**：按 [硬件接线与首次运行](docs/hardware/硬件接线与首次运行.md) 依次完成通信、1 mm、10 mm 和正式扫描检查。
5. **重算或换数据**：按下文安装 Python 依赖，运行示例或参数向导。

GitHub 网页不会执行交互 HTML，需下载后用浏览器打开。

## 一次实验的完整流程

```text
安装样品、确认起点和方向、采集暗场/透光参考
                     ↓
源表开始保存原始电流与每点时间戳
                     ↓
STM32 驱动 X 横扫 → Y 步进 → X 反向横扫
                     ↓
保存逐行有效运动边界、方向、停止时刻和实际参数
                     ↓
Python：识别有效横扫 → 像素分箱 → 奇偶方向重排
                     ↓
原始 I–point/I–t + 二维图 + 双向对应表 + 离线交互图
```

启动等待、垂直移动和掉头期间可以继续采集，原始数据完整保留。重构时用同步记录排除这些区间。缺少同步的旧记录可使用估计模式，但恢复的行边界不应视为经过标定的真实运动轨迹。

## 目录与阅读入口

| 目录/文件 | 内容 |
|---|---|
| `firmware/` | STM32 扫描逻辑、ZDT 协议、HAL/CMSIS、四个 Keil 工程 |
| `docs/hardware/` | 接线、扫描参数、故障处理、固件验证和资料来源 |
| `docs/异常加速排查.md` | X 轴途中突然加速的代码审查、假设和取证步骤 |
| `reconstruction/snake_scan/` | Python 输入校验、扫描窗口、像素聚合与交互查看器 |
| `reconstruction/examples/` | Z 胶带实测原始数据、参数、合成例子和解释图 |
| `reconstruction/results/` | 随仓库发布的全部结果与 SHA256 清单 |
| `reconstruction/docs/` | 阅读指南、数据格式、测量记录要求和扩展说明 |
| `reconstruction/outputs/` | 自己重新运行产生的结果，默认不进入 Git |

硬件入口：[固件说明](firmware/README.md) · [扫描参数](docs/hardware/参数与扫描路径.md) · [常见问题](docs/hardware/常见问题.md)。

测量与重构入口：[应该保存什么](reconstruction/docs/measurement.md) · [实验记录模板](reconstruction/docs/experiment.template.json) · [算法参数](reconstruction/docs/configuration.md) · [不规则像素分析](reconstruction/docs/artifacts.md)。详细文档保持中文。

## 平移台：硬件与运行

| 项目 | 仓库默认配置 |
|---|---|
| 控制器 | 野火小智 STM32F103C8T6 双 USB 款 |
| 下载器 | 野火 DAP，SWD |
| 电机 | ZDT X42S 第二代闭环步进，兼容 Emm V5 命令 |
| 串口 | USART1，PA9/PA10，115200、8N1，按硬件使用 TTL/RS485 |
| 轴地址 | X=2，Y=1 |
| 机械参数 | 1.8°步距角、16 细分、T6×1 丝杆，导程 1 mm/圈 |
| 默认扫描 | 100×100 mm、行距 2 mm、速度 1 mm/s |
| 状态灯 | PA1 红灯，低电平点亮 |

日常参数在 [snake_scan_config.h](firmware/Core/Inc/snake_scan_config.h)。用户报告的实测运行设置为 **2 mm/s，并修改过 Y 方向**；仓库默认头文件仍为 1 mm/s，不能把默认配置直接当成本次烧录参数记录。请保存实际烧录的配置与固件版本。

按顺序打开 `firmware/MDK-ARM/` 中的工程：

1. `01_COMM_CHECK_NO_MOVE.uvprojx`：只检查通信。
2. `02_1MM_MOTION_TEST.uvprojx`：X 往返各 1 mm，Y 累计 2 mm。
3. `03_10MM_MOTION_TEST.uvprojx`：X 往返各 10 mm，Y 累计 4 mm。
4. `04_ACTUAL_SNAKE_RUN.uvprojx`：使用配置中的正式范围。

每次修改参数或切换工程后重新编译、下载。正式运动在上电/复位后完成通信检查和 5 秒倒计时后启动一次。每条水平线完成后都执行一次 Y 步进，包括最后一条；实际水平线位置与最终停点见扫描参数说明。

程序没有机械回零、硬件限位或急停输入。运行前确认剩余行程；下载时关闭电机动力电源，保留可直接切断动力的开关。关于已报告的两次途中加速，请按 [专项排查文档](docs/异常加速排查.md) 记录并排查，不能仅因后续运行正常就确认问题消失。

## Python：重算与自己的数据

在项目根目录打开终端：

```bash
python -m pip install -r reconstruction/requirements.txt
python reconstruction/reconstruct.py run --config reconstruction/examples/z_tape/config.json --open
```

Windows 也可双击根目录 `run_reconstruction.cmd`。结果生成在 `reconstruction/outputs/z_tape/`，随项目保存的参考结果仍在 `reconstruction/results/z_tape/`。

用参数向导准备新实验：

```bash
python reconstruction/reconstruct.py wizard --output reconstruction/local/config.json
python reconstruction/reconstruct.py run --config reconstruction/local/config.json --open
```

| 模式 | 需要的信息 |
|---|---|
| `time_windows` | 每点时间戳、逐行有效匀速横扫起止时间和方向；支持非均匀采样 |
| `index_windows` | 逐行有效横扫起止下标和方向；行内采样需均匀 |
| `constant` | 稳定的行周期点数与首个完整周期起点 |
| `estimate` | 周期搜索范围、拟合区间和具有行间连续性的信号；用于缺同步的旧数据 |

所有模式还需数据路径、宽度、行距、每行像素数和阈值策略。积分时间不是采样间隔，约数启动等待也不能直接换算成点数。当前位置模型要求每行等宽、固定行距和有效横扫内匀速；非匀速编码器轨迹、多通道偏振量与自动采集是后续扩展。

## 实测结果与验证边界

Z 示例有 120,311 个原始采样，当前估计重构为 29×50 像素，每像素对应 77 或 78 个原始点。蓝色为低电流、黄色为高电流；没有按照片补画、去孤点或修整轮廓。起点、周期和换行占时不确定，图中还包含 I/导轨的真实遮挡。

Python 映射、发布快照和输入校验可运行：

```bash
python scripts/run_tests.py
python scripts/check_project.py
```

固件在本次合并中保持原有运动代码；工程路径与参数引用做静态检查。没有执行烧录或机械实测，静态检查不能代替硬件验证。原验证表见 [固件验证记录](docs/hardware/验证记录.md)。

## 许可与维护

自有代码、说明和实测示例按各自 [LICENSE](LICENSE)、[重构许可](reconstruction/LICENSE) 保留。ST、Arm 和 ZDT 的原有声明见 [第三方说明](THIRD_PARTY_NOTICES.md)。

本仓库是后续统一维护入口。原重构仓库保留历史并指向这里，不再作为独立功能项目更新；迁移说明见 [合并记录](docs/项目合并记录.md)。
