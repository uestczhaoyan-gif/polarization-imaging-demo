# 合成数据验证

本例由程序生成，具有已知二值图、非均匀采样时间戳和正反向行记录，用来验证映射逻辑。它与两个实测案例分开，不作为实验测量结果。

[交互结果](results/viewer.html) · [已知二值答案](expected_binary.csv) · [原始数据](data.csv) · [行时间窗](rows.csv) · [配置](config.json)

从项目根目录运行：

```bash
python reconstruction/reconstruct.py run --config experiments/synthetic/config.json
```

`generate.py` 可重新生成输入与答案；发布结果在 `results/`，自己重算的结果在根目录 `local/reconstruction/synthetic/`。

## 单实验复现入口

[code/reconstruct.py](code/reconstruct.py) 调用公共算法和本实验配置，结果写到根目录 local/reconstruction 下。请下载完整项目并安装 reconstruction/requirements.txt，再从根目录运行 `python experiments/synthetic/code/reconstruct.py`。原有分析脚本保留原路径。
