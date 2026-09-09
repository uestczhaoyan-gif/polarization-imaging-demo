# 第一次使用：按什么顺序读

## 只想先看实验结果

1. 下载整个项目并解压，打开根目录的 `README.md`。
2. 双击 `open_results.cmd`；或在浏览器中打开 [Z 实测交互图](../results/z_tape/viewer.html)。不需要 Python、不需要联网。
3. 先看 [完整原始 I–point 曲线](../results/z_tape/01_raw_I_point.png)，再看 [二维重构与混合采样占比](../results/z_tape/02_reconstruction.png)。图中 point 为连续十进制采样索引，不是秒。
4. 阅读 [不规则像素分析](artifacts.md)，理解目前的分行、起点、转向比例都是缺少同步时的估计。

GitHub 网页只能预览 HTML 源码；先下载才可以交互。不要只保存网页截图。项目中的 `results/` 已包含本次完整结果，不必先安装依赖才能查看。

## 怎样让两幅图对应

左图每个格子表示一个二维像素。点击后会同时更新右侧两张图和下方全记录：

- 红框：选中的二维像素。
- 右上整条扫描行：仍按真实采集顺序画；黄色区间表示这个像素的数据。
- 右下局部图：这个像素的全部原始采样，红虚线为当前阈值。
- 下方完整曲线：黄色标记整行，红色标记像素。点击任意曲线位置，可以反查对应像素。

先在行号/列号输入 `(7,41)`：它对应 point 30583～30659，共 77 点，中位数约 12.4 μA，高采样占比约 50.6%。这个例子能说明一个像素为什么会混合边缘两侧的信号。

再看 `(12,24)`：point 51903～51980，共 78 点，中位数约 3.69 μA，属于较平稳的低电流区域。

每一行的正/反方向会在图标题中标明。反向行从时间上先扫到的位置，对应二维图中较靠右的像素，这是蛇形扫描的正常结果。所有行列和点下标从 0 开始。

把图像模式切到“高电流采样占比”，可查看混合程度；占比不是正确率或错误概率。临时调整阈值可以观察哪些格子改变，但不会覆盖 Python 生成的正式矩阵。

## 怎样读原始文件与 CSV

原始文件是 [examples/z_tape/data/raw_data.txt](../examples/z_tape/data/raw_data.txt)：第一列电流，单位 A；第二列是仪器导出的点号文本。本例点号为八进制，程序按连续性识别后转成连续十进制索引；不要直接按十进制跳号补数据。

需要追溯某一像素时，打开 [pixel_to_points.csv](../results/z_tape/pixel_to_points.csv)：

| 字段 | 读法 |
|---|---|
| row、col | 二维行、列，从 0 开始 |
| start_source_index | 第一条对应原始记录 |
| stop_source_index_exclusive | 结束边界，不包含这一条 |
| sample_count | 像素内原始采样数 |
| median_current_A | 决定二值颜色的中位数，单位 A |
| std_current_A | 原始点的总体标准差，单位 A；不是空间定位误差 |
| high_sample_fraction | 原始点超过阈值的比例 |
| binary_0_low_1_high | 0 低电流，1 高电流 |

`start=30583, stop=30660` 对应 Python `current[30583:30660]`，正好是 77 点。若想从原始点反查像素，使用 [sample_to_pixel.csv](../results/z_tape/sample_to_pixel.csv)。行列为 -1 表示未参与图像，仍保留在全记录中。

`binary_image.csv` 是最终 0/1 矩阵；`current_image_uA.csv` 是每像素中位数，注意这里单位为 μA。`metadata.json` 记录阈值、行窗口、版本和原始数据校验值。`reconstruction.npz` 把原始数据与对应数组放在一起，可按 [参数说明中的 Python 示例](configuration.md#空间坐标与数据对应)读取。

## 想自己运行或换数据

按 README 安装依赖，先双击 `run_example.cmd` 重算这次 Z 实测例子。新结果写在 `outputs/z_tape/`，与 `results/z_tape/` 发布快照分开保存。

然后读 [参数与数据格式](configuration.md)，使用 `configure_scan.cmd` 或参数向导创建自己的 JSON 配置。优先使用有时间戳和逐行实际窗口的模式；estimate 用于没有同步记录的旧数据补救。

在开始新测量前读 [测量清单](measurement.md)，复制 [完整实验记录模板](experiment.template.json)。实验记录模板描述全部测量条件；重构配置描述本次算法所需参数，它们是两个用途不同的 JSON 文件。

想扩展仪器输入、多通道或位置反馈，再读 [开发说明](development.md)。
