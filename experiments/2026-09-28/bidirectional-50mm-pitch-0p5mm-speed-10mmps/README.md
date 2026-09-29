# 细行距快速扫描：采样点减少，行间差异增大

## 设置

双向；范围50×50 mm；行距0.5 mm；X设定10 mm/s，旧程序Y同速；100行；原始57,654点。

100×100像素，名义格距0.5×0.5 mm；每像素3–5个原始点。

秒表第二段13.16分钟，首段28.27秒。用户确认首段近似为开始运动，存在误差，结束还可能含等待；不是逐点时间戳。

## 结果解读

两个窗口可辨识，但窗口边缘及右窗口出现交替条纹，左窗口上部也有位移或形变。

名义像素更细并不保证有效分辨率更高。每像素只有3–5点，运动/响应迟滞、采样不均匀和分行相位都可能放大行间差异。用户报告此配置机械振动较大且Y换行过快。

所有图像的像素值均为原始电流中位数，无阈值化、无图像平滑。分行使用估计的远端电流平台；条纹可能同时包含真实信号变化和配准误差。

## 文件

- [完整原始波形](results/01_raw_I_point.png)
- [连续电流重构](results/02_current_reconstruction.png)
- [交互查看器](results/viewer.html)：下载后直接打开，点击像素或曲线双向定位。
- [原始数据](data/current.xls)、[配置](config.json)、[估计行窗口](estimated-row-windows.csv)
- [逐像素原始点范围](results/pixel_to_points.csv)、[逐点像素映射](results/sample_to_pixel.csv)

[本次总说明与处理方法](../README.md)

## 本实验的目录与复现

- [data/](data/)：未经改写的原始采集数据。
- [results/](results/)：发布的图像、交互查看器和逐像素对应表。
- [code/reconstruct.py](code/reconstruct.py)：只复现本实验的代码入口。
- [config.json](config.json)：参数；[estimated-row-windows.csv](estimated-row-windows.csv)：估计的分行区间。
- [现场照片及时间记录](../setup/)：本批次共用资料，原文件对应关系见其中 sources.json。

下载并解压完整仓库，在仓库根目录执行 `python -m pip install -r reconstruction/requirements.txt`，然后执行 `python experiments/2026-09-28/bidirectional-50mm-pitch-0p5mm-speed-10mmps/code/reconstruct.py`。新结果输出到根目录 `local/reconstruction/2026-09-28/` 下的同名实验文件夹，保留发布结果。公共算法在根目录 reconstruction 中；请下载完整仓库，不要只复制入口脚本。

## 位置对应敏感性检查

[相位、像素宽度和正反向行拆分对照](results/registration-check/README.md)。这是探索性诊断，不是位置校准，也不替换上面的原结果。
