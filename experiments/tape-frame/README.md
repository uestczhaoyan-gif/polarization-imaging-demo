# 80×80 mm 暗环境测量

源文件：`I-t采集数据2026.09.09--21-16-34.xls`，原样保存在 [data/raw_export.xls](data/raw_export.xls)。虽然扩展名是xls，内容是GB18030编码的电流(A)与八进制点号文本，不是Excel二进制工作簿。

## 直接查看

- [完整原始 I–point](results/anchored/01_raw_I_point.png)
- [实物照片与二维图对应说明](photo-comparison.md)：矩形胶带框、中央透光窗口及红光起点。
- [波形辅助分行的双色估计图](results/anchored/02_reconstruction.png)
- [固定周期对照图](results/uniform/02_reconstruction.png)
- [互动对应图](results/anchored/viewer.html)：下载后在浏览器打开，点击像素能查看原始点，点击曲线能反查像素。

蓝色表示低电流，黄色表示高电流。阈值由原始数据的Otsu方法计算，约30.426 μA；它不是新的硬件逻辑电平，也不直接等于偏振量。没有按照片补画或删除孤立像素。

## 已知条件与未知条件

用户记录：起点在矩形左上角、光敏电阻被挡光，扫描80×80 mm、2 mm/s、暗环境；测量开始后等待约12.8秒，运动约28分40秒，误差约一分钟。途中再次出现一次快速横移。行距暂沿用2 mm，因此先按40条水平扫描线、每行40个像素重构；应以实际配置为准。最后水平线位于相对Y=78 mm，末尾Y步进可到80 mm。

已补入本次 [实物照片](sample_photo.jpg)：黑色胶带围成矩形框，红光点位于外框左上角；中央透光窗口与估计图的主要结构相符。照片只用于外观比对，未用于调整阈值、分行或补画像素，详见 [对应说明](photo-comparison.md)。文件有20,059个采样，八进制编号连续，没有编号缺失，但没有每点时间戳、逐行起止时刻、停止标记或编码器位置。因此：

- 原始图横轴使用真实的记录顺序 point。不能把点号当秒，也不能用源表界面的0.1直接当采样间隔。
- 12.8秒等待无法唯一换算成起始下标。约1720秒运动时长也不能证明整个文件覆盖恰好这1720秒。
- 40条80 mm横扫的理想匀速时间合计1600秒；40次2 mm垂直步进合计40秒，另有通信、换轴等待、到位轮询。报告的总时长与这一量级相容，但不足以给每个像素定位。

## 两种图为什么不同

固定周期对照用每行485.75点、起点107点、横扫占周期94%，显示匀速/固定采样假设被破坏时的错行；参数是估计，并非仪器标定。

波形辅助结果使用20个重复高平台（电流经9点中值滤波后大于64 μA，持续超过20点），把平台中心假设为每次往返的同一相位，再线性插值得到40行并排除每行前后各3%的换行区间。**滤波仅用于寻找参照平台，像素仍聚合完整原始电流。** 全部平台在 [waveform_anchors.csv](waveform_anchors.csv)，行区间在 [estimated_windows.csv](estimated_windows.csv)。

平台间隔中位数为971.5点；第2个平台中心1609与第3个平台中心2395.5之间只有786.5点，较中位数短约19%。它证明波形周期不恒定，不证明电机加速19%，也不能排除采样节奏或光学变化。该区间跨越估计第4、5行（从1开始）；首行和末行还使用了外推。它们的几何解释尤其不可靠。

重复平台不是行同步传感器。这个方法假设样品在同一侧存在稳定重复特征，不能用于任意图案。相位选错也会使奇偶行错位。本例的 [分行敏感性比较](results/03_timing_sensitivity.png) 展示这一影响。

**若发生真实快速移动，异常段的等点数像素不再等距离，可能局部压缩、拉伸；若该行提前结束，固定分行还会让后续所有行错位。** 波形辅助分行只能缓解周期漂移，不能恢复这段未知速度轨迹，更不能补回没有采到的空间信息。

## 用简明代码重算

在整个项目根目录运行：

```bash
python -m pip install -r reconstruction/requirements.txt
python reconstruction/simple_reconstruct.py
python reconstruction/simple_reconstruct.py --config experiments/tape-frame/config-constant-period.json
```

[simple_reconstruct.py](../../reconstruction/simple_reconstruct.py) 是日常入口。只需读五步：读取、指定行区间、等分像素、反向行翻转、导出。绘图和网页细节复用底层模块，不需要日常修改。主结果输出到 `local/reconstruction/tape-frame/`，不会覆盖随仓库发布的结果。

自己的数据建议先复制 [config-constant-period.json](config-constant-period.json)，修改数据路径、宽度、行距、行数、像素列数、起始下标、每行周期点数和有效横扫占比；必须已有可信的采样/行记录才能填写这些数。若已经保存逐行点区间，就改用 `row_windows_csv`。真实时间戳且采样不均匀时使用完整入口的 `time_windows` 模式。不要把本例的485.75点、107点或64 μA检测阈值套用到下一次测量。

重新生成本例探索性行窗口：

```bash
python experiments/tape-frame/prepare_windows.py
```

原始文件SHA256：`079a4905b7261c008347127aea21e42735a4a85c0fd46b373dfa4ef5f352c514`。主估计图使用18,280点，其余1,779点保留在原始曲线和对应表中，标记为未用于图像。每个像素包含9–12个原始点。详细测量记录要求见 [measurement.md](../../docs/reconstruction/measurement.md)，复位和加速问题见 [专项排查](../../docs/hardware/reset-and-vendor-checklist.md)。
