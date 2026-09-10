# 参数与数据格式

## 四种模式

`time_windows` 在每行 `[start_s,stop_s)` 内均分时间，然后用 `searchsorted` 找实际采样下标；同一行各像素点数可以不同。前提是扫描匀速、每行覆盖同样宽度、时钟同步。时间窗不得超出数据覆盖范围，建议保留扫描前后采样。程序不会外推末行。

`index_windows` 直接在有效横扫下标区间均分点数，要求该行采样均匀。CSV：

```csv
start_point,stop_point_exclusive,direction
1000,4900,forward
5100,9000,reverse
```

`constant` 每条完整周期为 `[start_point+rP,start_point+(r+1)P)`，P=`samples_per_row`。其中 `turnaround_fraction` 的一半从周期前后各排除；剩下的才分像素。这个对称假设未必匹配真实转向，已有行窗口时应优先用窗口模式。

`estimate` 在显式 `row_period_search=[下限,上限]` 中估计周期，以相邻行反向重排后的一致性估计起点。拟合数据范围由 `fit_point_range=[开始点,结束点)` 指定；至少覆盖 6 个最长候选周期。中值滤波只辅助分行，不改变最终聚合用的原始数据。此模式偏好连续图案，不适合任意棋盘或强周期纹理，不能保证唯一解。

行窗口 CSV 中每一行都写 `direction`，以显式记录为准，可处理同向行；`first_row_reverse` 只用于周期模式。各模式均按窗口采集顺序放置 Y 行，默认第一行在上；如果实际方向不同，请在实验记录中说明。任意 Y 坐标、漏行、非均匀行距尚不支持。

## 参数表

| 参数 | 单位/值 | 说明 |
|---|---|---|
| `input_file` | 路径 | 原始数据；相对配置文件目录 |
| `input_format` | `csv` / `legacy` | 标准 CSV 或旧 I(A)+点号文本 |
| `mode` | 四种模式之一 | 显式选择，程序不自动猜模式 |
| `output_dir` | 路径 | 默认 `outputs`，相对配置文件目录 |
| `width_mm` | 正数，mm | 每条有效横扫覆盖宽度；用于名义坐标 |
| `line_step_mm` | 正数，mm | 相邻扫描线实际间距 |
| `columns` | 正整数 | 每行像素数 |
| `threshold_uA` | μA 或 `null` | 固定阈值或 Otsu；允许负电流阈值，但须在信号范围内 |
| `minimum_samples_per_pixel` | 正整数，默认 1 | 不足时直接报错；不插值补齐空像素 |
| `row_windows_csv` | 路径 | 两个窗口模式必填 |
| `sample_interval_seconds` | 正数，s | 没有 time_s 时用已知固定采样间隔建立时间轴；仅假设均匀 |
| `max_sample_gap_seconds` | 正数，s 或 `null` | 时间窗模式下允许的最大采样间断，超出报错 |
| `samples_per_row` | 正数，点 | constant 必填；含转向的完整周期 |
| `start_point` | 非负数，点 | constant 必填；首条完整周期起点，可为小数 |
| `turnaround_fraction` | [0,0.2) | 周期模式的转向占比假设，默认 0 |
| `first_row_reverse` | JSON 布尔 | 周期模式首行是否反向，默认 false |
| `row_period_search` | 两个点数 | estimate 必填，周期搜索区间 |
| `fit_point_range` | 两个整数点号 | estimate 必填，拟合范围 |
| `alignment_median_window` | 正奇数，点 | 默认 31，仅用于估计分行 |
| `point_base` | `auto` / 8 / 10 | 仅 legacy 读取；auto 检验连续性 |
| `reported_start_wait_seconds` | 秒或 `null` | 启动等待约数，仅作实验记录，不自动裁剪 |
| `reported_speed_mm_s` | mm/s 或 `null` | 仅记录，不据此伪造采样率 |
| `title` | 文本 | 查看器标题 |

未知额外字段会保存在配置快照中，但不会自动影响算法；请按本表核对拼写。Z 配置中的 `roi_x_mm` 是原示例裁剪范围记录，新通用查看器显示完整图，不据此删除区域。

已有 `time_s` 时不得再填写固定采样间隔。是否有时间轴与是否有真实同步是两回事：`metadata.time_source` 区分仪器时间戳和用户固定间隔假设。可在点数模式下展示 I–t，但点数分箱仍假设均匀采样；非均匀采样应改用 time_windows。

## 最小时间窗配置

```json
{
  "input_file": "measurements.csv",
  "input_format": "csv",
  "output_dir": "outputs/run01",
  "mode": "time_windows",
  "row_windows_csv": "rows.csv",
  "width_mm": 100,
  "line_step_mm": 2,
  "columns": 50,
  "threshold_uA": 12,
  "minimum_samples_per_pixel": 5,
  "max_sample_gap_seconds": 0.1
}
```

以上数字只是格式示例。`minimum_samples_per_pixel` 和间断阈值要按实际采样、像素驻留时间与可接受缺失调整。缺失像素目前报错，不把缺失误编码成低电平。

## 空间坐标与数据对应

第 c 列名义中心为 `(c+0.5)*width_mm/columns`；CSV 第 r 扫描线位置为 `r*line_step_mm`。静态图把每行画成一个行距高的单元，Y=0 为首行单元上缘，与 CSV 线坐标有半个显示单元的区别，不代表额外运动。

`pixel_to_points.csv` 保存像素下标、点号区间、中位数、均值、标准差、高采样占比和二值分类。`sample_to_pixel.csv` 保留每个原始点、原始点号、时间和反查行列；行列 -1 表示未使用。原始数组从不因为蛇形扫描而原地翻转。

```python
import numpy as np
d = np.load('outputs/run01/reconstruction.npz', allow_pickle=False)
r, c = 7, 41
a, b = d['limits'][r, c]
pixel_samples_A = d['raw_current_A'][a:b]
print(a, b, len(pixel_samples_A), np.median(pixel_samples_A))
```

## 常见错误

- 模板里周期/范围为 `null`：必须填写本次值，或使用向导。
- 文件读取失败：检查相对路径基准是 config 所在目录；标准 CSV 必须有 `current_A` 列。
- 点号不连续：先查仪器缓存/导出；不要简单重编号假装没有丢点。
- 空像素/点数不足：减少列数、检查长采样中断或真实时间窗，不用插值填成“测到了”。
- 时间窗超出覆盖：保留扫描后数据或只列出完整横扫，不硬造最后一行。
- 输出目录非空：使用新目录，或加 `--overwrite`；输入和配置与输出分开放。
- 整幅左右镜像：周期模式检查 `first_row_reverse`，窗口模式检查实际方向；无需重排原始电流。
