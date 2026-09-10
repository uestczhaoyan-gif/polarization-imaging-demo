# 随项目提供的完整结果

这里保存原重构v1.1.0的结果以及统一项目v2.1.0新增的暗环境结果，随 Git 仓库和完整 ZIP 一起提供。查看结果不用安装 Python；重新计算的结果默认写入 `reconstruction/outputs/`。

- [Z 胶带实测交互图](z_tape/viewer.html)：120,311 个原始点，29×50 像素的估计重构。
- [合成数据交互图](synthetic/viewer.html)：非均匀时间戳与正反向扫描，具有已知答案。
- [80×80 mm 暗环境交互图](dark_80mm_20260909/anchored/viewer.html)：20,059个原始点、40×40像素，波形辅助分行估计；含快速横移的不确定区间。[固定周期对照](dark_80mm_20260909/uniform/02_reconstruction.png) · [相位敏感性](dark_80mm_20260909/03_timing_sensitivity.png)。
- [结果校验清单](manifest.sha256)：本目录生成文件的 SHA256；原始数据校验值另保存在各例子的 metadata.json。

GitHub 网页不会执行 HTML 交互代码，请下载到本地并用现代浏览器打开。

## 各文件怎么用

| 文件 | 内容 |
|---|---|
| `01_raw_I_point.png / .svg` | 全部原始采样，不滤波的 I–point 曲线 |
| `01b_raw_I_time.png` | 有时间轴时才生成的 I–t 图；Z 实测数据没有真实时间戳 |
| `02_reconstruction.png / .svg` | 二值图与高电流采样占比图 |
| `viewer.html` | 完整数据内嵌的双向交互图，可独立复制使用 |
| `binary_image.csv` | 0 低、1 高的二维矩阵 |
| `current_image_uA.csv` | 每像素电流中位数，μA |
| `pixel_to_points.csv` | 每个像素对应的原始点区间和统计 |
| `sample_to_pixel.csv` | 所有原始点及它们对应的行列，未使用为 -1 |
| `row_windows.csv` | 本次实际采用的窗口、方向和有效点区间，含单位域 |
| `reconstruction.npz` | 原始数组、图像、映射及 JSON 元数据 |
| `metadata.json` | 输入 SHA256、参数、版本、窗口和使用点数 |
| `analysis.json`（Z 示例） | 周期/阈值敏感性和混合像素统计 |

早期解释图（启动段、像素对应示例、Z 裁剪图）也一并保存在 [examples/z_tape/reference/](../examples/z_tape/reference/)，不会在新一次运行时覆盖。

## 维护结果快照

项目维护者可在整个项目根目录运行 `python reconstruction/scripts/build_example_results.py`，重新生成三个例子的结果和校验清单。该脚本明确写入 `results/`；普通用户运行 `reconstruct.py run` 则按配置写入 `outputs/`。

结果中的名义坐标、估计行边界及相应局限见 [实验分析](../docs/artifacts.md)。快照是可复现的处理结果，不是经过硬件同步标定的真实位置标签。
