# light60

单向扫描；X范围 55 mm，20 行，Y行距1 mm；X设定 1 mm/s；NPLC=0.1。原始178,870点，成像20×55像素。

[原始波形及使用区间](results/00_raw_with_windows.png) · [连续电流图](results/02_current_reconstruction.png) · [逐像素查看器](results/viewer.html) · [原始数据](data/current.xls) · [秒表照片](data/stopwatch.jpg)

[配置](config.json) · [分行区间](estimated-row-windows.csv) · [像素到原始点](results/pixel_to_points.csv) · [逐点用途](results/sample_roles.csv) · [单实验复现入口](code/reconstruct.py)

数据无逐点时间戳，图像坐标为计时模型下的名义坐标。尾部、回程、换行数据未参加正向成像，但都保留。逐点用途中的非正扫类别只是估计，不能视为电机实际事件日志。

安装根目录 reconstruction/requirements.txt 后运行本实验 code/reconstruct.py；新输出写入根目录 local/reconstruction/2026-10-16。同批次所有窗口与结果可用上级批次 rebuild.py 重建（会覆盖生成结果）。

[批次分析与结论](../../README.md) · [离线图集](../../index.html)
