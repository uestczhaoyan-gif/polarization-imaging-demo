# 按实验查找数据、结果和代码

每个实测实验有独立文件夹。先选择实验，再打开 data（原始数据）、results（结果）或 code（复现入口）。0928 实验按日期归为一批，五个实验在批次内平行排列。

| 实验 | 实验文件夹（设置、数据、结果、代码入口） |
|---|---|
| 早期：胶带 Z 字母 | [tape-z](tape-z/README.md) |
| 早期：矩形胶带框 | [tape-frame](tape-frame/README.md) |
| 0928：细行距快速扫描：采样点减少，行间差异增大 | [bidirectional-50mm-pitch-0p5mm-speed-10mmps](2026-09-28/bidirectional-50mm-pitch-0p5mm-speed-10mmps/README.md) |
| 0928：细行距慢速扫描：两个窗口清晰，局部响应仍不均匀 | [bidirectional-50mm-pitch-0p5mm-speed-1mmps](2026-09-28/bidirectional-50mm-pitch-0p5mm-speed-1mmps/README.md) |
| 0928：较大行距快速扫描：时间更短，竖向采样更稀 | [bidirectional-50mm-pitch-1mm-speed-10mmps](2026-09-28/bidirectional-50mm-pitch-1mm-speed-10mmps/README.md) |
| 0928：光强分级扫描：连续电流保留强度变化 | [intensity-steps-50mm-pitch-2mm-speed-5mmps](2026-09-28/intensity-steps-50mm-pitch-2mm-speed-5mmps/README.md) |
| 0928：单向扫描：只使用正向横扫，回程不参与成像 | [unidirectional-80mm-pitch-2mm-speed-1mmps](2026-09-28/unidirectional-80mm-pitch-2mm-speed-1mmps/README.md) |
| 合成验证（非实测） | [synthetic](synthetic/README.md) |

[直接看全部0928结果图](../RESULTS.md) · [0928设置总表与处理方法](2026-09-28/README.md) · [原始文件远端核验清单](2026-09-28/source-backup-verification.json)

共用重构算法放在根目录 reconstruction，共用电机固件放在 firmware。实验代码入口引用公共实现，避免复制多份算法后版本不一致。早期实验原有分析脚本保留原路径，以保持历史复现命令可用。

每个 results 是已发布快照；复现输出放到根目录 local。0928的现场照片集中在该批次 setup 中，由每个实验链接进入。原始运动参数测试目录按要求未上传。
