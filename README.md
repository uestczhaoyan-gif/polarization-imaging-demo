# 偏振成像演示

支持双向蛇形与单向扫描，可在START.cmd工作台切换。单向每行横扫后返回，再Y换行（最后一行也一样）；返回段不用于成像。模式不会自动控制源表或生成同步日志。[模式、时间与重构说明](docs/hardware/scan-modes.md)

**中文** | [English](README.en.md)

STM32 控制双轴平移台做蛇形扫描，源表记录电流，Python 将采样重构为二维图像。项目包含固件、图形化参数编辑器、两个实测案例和可逐像素反查原始数据的离线查看器。

目前实现单通道电流空间成像；源表仍由仪器软件采集，没有电机—源表同步触发，也不计算 Stokes 参数或偏振度。

## 从这里开始

下载 [完整项目包](https://github.com/uestczhaoyan-gif/polarization-imaging-demo/releases/latest)，解压后：

1. **修改电机参数**：双击唯一的启动入口 `START.cmd`。填写范围、速度和方向（支持0.5、0.1 mm等小数行距），检查预览后保存，再到 Keil 编译、下载。[界面使用说明](docs/hardware/configuration-ui.md)
2. **查看测量结果**：在工作台“实验与使用指南”页选择案例，打开交互结果；也可直接打开下表中的 `viewer.html`。查看结果不需要 Python。
3. **开始新测量**：先读 [接线与首次运行](docs/hardware/wiring-and-first-run.md) 和 [测量记录清单](docs/reconstruction/measurement.md)，保留实际参数、时间戳与逐行运动记录。
4. **理解或修改重构**：先看 [核心处理过程](docs/reconstruction/core-process.md)，再运行下面的示例。

工作台需要 Python 3.10+（含 Tkinter），不需要安装第三方库；macOS/Linux 运行 `python tools/control_panel.py`。GitHub 不能直接执行交互 HTML，请下载后打开。

## 两个实测案例

| 案例 | 数据、配置与说明 | 已保存结果 |
|---|---|---|
| 胶带 Z 字母 · 环境光 | [tape-z](experiments/tape-z/README.md)：120,311点，缺少同步记录 | [交互图](experiments/tape-z/results/viewer.html) · [重构图](experiments/tape-z/results/02_reconstruction.png) |
| 矩形胶带框 · 暗环境 | [tape-frame](experiments/tape-frame/README.md)：20,059点，80×80 mm | [交互图](experiments/tape-frame/results/anchored/viewer.html) · [照片与对应说明](experiments/tape-frame/photo-comparison.md) |

两个文件夹地位相同：各自保留原始数据、参数、实验说明和 `results/`。另有 [合成验证案例](experiments/synthetic/README.md)，用于核对算法，不属于实测数据。

## 项目目录

```text
START.cmd                 Windows 统一工作台入口
firmware/                 STM32 固件与四个 Keil 工程
tools/                    参数界面与独立参数校验模块
reconstruction/           Python 重构代码与测试
experiments/
  tape-z/                 Z 字母：数据、配置、说明、结果
  tape-frame/             矩形框：数据、配置、照片、结果
  synthetic/              已知答案的合成验证
  manifest.sha256         全部已发布结果的校验清单
docs/                     硬件、重构、模板与项目维护文档
scripts/                  维护者检查与发布工具
local/                    本地配置备份和新生成结果（不上传）
```

所有文档从 [文档目录](docs/README.md) 进入；文件命名和历史目录对应见 [目录规范](docs/project/layout.md)。固件内部保留 Keil/CubeMX 的标准目录与工程名称。

## 运行重构

以下命令均在项目根目录执行：

```bash
python -m pip install -r reconstruction/requirements.txt
python reconstruction/simple_reconstruct.py --config experiments/tape-frame/config.json
python reconstruction/reconstruct.py run --config experiments/tape-z/config.json --open
```

新结果写入 `local/reconstruction/<案例>/`；发布快照仍保留在各案例 `results/`。完整入口默认拒绝覆盖已有输出，确需重算时加 `--overwrite`。自己的实验先复制配置并填写本次记录，不能沿用案例估计的点数周期。[重构模块说明](reconstruction/README.md)

## 固件和验证边界

控制器为 STM32F103C8T6，ZDT X42S 双轴电机；X地址2、Y地址1。仓库默认100×100 mm、行距2 mm、速度1 mm/s。工作台编辑 [snake_scan_config.h](firmware/Core/Inc/snake_scan_config.h)，保存配置不等于已烧录。四个 Keil 工程按通信检查、1 mm测试、10 mm测试、正式扫描依次使用。[固件说明](firmware/README.md)

已报告的快速横移和复位异常尚未定位。小数行距版本增加了接收确认、名义运动时间和连续到位状态检查；主机模拟通过不代表实机异常已解决。[运动异常](docs/hardware/motion-anomalies.md) · [复位与商家排查](docs/hardware/reset-and-vendor-checklist.md)

没有位置日志的实测图使用估计分行，未按照片补画。软件检查不替代烧录、接线和实际运动验证。项目没有机械回零、硬件限位或急停输入，首次运行请按硬件指南检查行程与断电手段。

维护检查：`python scripts/check_project.py`、`python scripts/run_tests.py`。

自有代码见 [LICENSE](LICENSE) 与 [重构许可](reconstruction/LICENSE)；保留 [第三方声明](docs/project/third-party-notices.md)。两个原项目的历史均已合并，后续统一在本仓库维护。[更新记录](docs/project/changelog.md)
