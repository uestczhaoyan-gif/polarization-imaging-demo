# 蛇形扫描电流图像重构

Python 离线例程：连续电流 → 二维高低电平图，并保存像素与原始点的双向对应。支持参数向导、四种重构模式、CSV/NPZ/PNG/SVG 输出及无需联网的交互查看器。

用于平移台透射/遮挡扫描和教学。可配合 [STM32 + ZDT 双轴平移台控制](https://github.com/uestczhaoyan-gif/stm32-zdt-xy-stage)。本程序不直接驱动电机，尚不计算偏振度、偏振角或 Stokes 参数。

## 运行合成例子

```bash
python -m pip install -r requirements.txt
python reconstruct.py run --config examples/synthetic/config.json --open
```

Windows 可以双击 `run_example.cmd`。结果在 `outputs/synthetic/`；双击 `viewer.html` 即可离线打开，不用安装浏览器插件或启动服务。GitHub 文件预览不执行交互图，请下载后运行。

合成数据由 `examples/synthetic/generate.py` 使用固定随机种子生成，模拟非均匀时间戳与两条正反向扫描行。两行已知答案均为 `[低, 高, 高]`，用于验证时间分箱与方向处理，不代表实测数据。

## 把两幅图对应起来

1. 点击二维图的一个像素，或输入行号/列号。
2. 右侧上图显示对应扫描行，黄色区间为该像素；右侧下图显示像素内所有原始采样。
3. 下方完整曲线标出该行和像素，点击曲线可反查二维像素。
4. 未用于建图的等待/转向点明确标记；可切换高采样占比、调整阈值和导出选中像素 CSV。

全部索引从 0 开始，区间 `[a,b)` 不包含 b。原始曲线始终保留采集顺序；反向行只反转空间对应。浏览器内调整阈值不会覆盖 Python 输出。总览使用最小—最大包络绘制密集波形，局部像素图显示全部原始点。

## 输入自己的参数

```bash
python reconstruct.py wizard --output local/config.json
python reconstruct.py run --config local/config.json --open
```

也可以用 `python reconstruct.py init --mode time_windows --output local/config.json` 生成模板。所有相对路径以 config 所在目录为准；未知值不要编造。输出目录非空时需换目录或明确加 `--overwrite`。

| 模式 | 所需信息 |
|---|---|
| time_windows | 每点时间戳，每行有效匀速横扫起止时间和方向；支持非均匀采样 |
| index_windows | 每行有效横扫起止点下标和方向；要求行内均匀采样 |
| constant | 每行周期点数、首个完整周期起点；要求周期和采样稳定 |
| estimate | 周期搜索范围、拟合点号区间；缺少同步时的估计，可能多解 |

全部模式还需数据路径、扫描宽度、行距和每行像素数。阈值可固定或设 null 使用 Otsu，需确认信号可分为两类。输入格式及完整参数见 [配置说明](docs/configuration.md)。

CSV 数据列为 `point,time_s,current_A`，point 和 time_s 可省略；电流为 A、时间为秒。time_s 须有限、严格递增；不能用积分时间替代采样间隔。旧“两列 I(A)、点号”文本可用 legacy 格式。

## 测量时保存什么

- 每点原始电流、真实时间戳、点号和仪器状态。
- 每行有效运动开始/结束、方向、行号、停止时刻及尽可能多的位置反馈。
- 宽度、行距、速度、加速度、起点、实际行数与固件版本。
- 源表型号、量程、积分值及单位、自动归零、滤波与触发方式。
- 暗场、透光参考、光斑大小、安装方向、环境照明；偏振实验另存角度和通道。

完整 [测量清单与保存模板](docs/measurement.md)、[不规则像素诊断](docs/artifacts.md)。

## 代码结构与验证

`snake_scan/pipeline.py` 负责校验、扫描窗口与聚合；`core.py` 负责兼容读入和周期估计；`report.py` 输出报告；`viewer.html` 提供交互；`cli.py` 提供命令行和参数向导。[扩展说明](docs/development.md)。

```bash
python -m unittest discover -s tests -v
```

亦可 `python -m pip install -e .` 安装为 `snake-scan` 命令。自动测试配置覆盖 Windows/Ubuntu、Python 3.10/3.12。

程序保留全部原始点，未使用的点映射为行列 -1；空像素报错，不插值补画。输出中保存参数、原始数据 SHA256、库版本和双向 CSV。当前位置模型要求每行同宽、固定行距、有效横扫内匀速；任意编码器轨迹、缺失掩码和多通道定量是后续扩展。

代码和合成示例采用 [MIT 许可](LICENSE)。
