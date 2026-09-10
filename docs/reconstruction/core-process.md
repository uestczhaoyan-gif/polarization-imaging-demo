# 重构核心：从一维电流到二维像素

核心流程是：**确定行窗口 → 行内等分 → 每组取中位数 → 反向行翻转 → 阈值分类**。文件读写、画图和网页是辅助部分，不参与位置推断。

```python
import numpy as np

def reconstruct_core(current, windows, reverse, threshold, columns=40):
    image = np.empty((len(windows), columns))
    point_ranges = np.empty((len(windows), columns, 2), dtype=int)
    for row, (start, stop) in enumerate(windows):
        edges = np.ceil(np.linspace(start, stop, columns + 1)).astype(int)
        for group, (a, b) in enumerate(zip(edges[:-1], edges[1:])):
            if b <= a:
                raise ValueError('一个像素至少需要一个采样点')
            col = columns - 1 - group if reverse[row] else group
            image[row, col] = np.median(current[a:b])
            point_ranges[row, col] = [a, b]
    binary = (image >= threshold).astype(np.uint8)
    return image, binary, point_ranges
```

这是用于review的核心摘录；运行入口还检查窗口越界、重叠、方向和参数。所有区间为 `[start, stop)`，不含末点，下标从0开始。`binary=0` 为蓝色、`1`为黄色。

蛇形第二行先采到右侧的点，翻转的是该组对应的空间列；原始采样数组保持采集顺序。每个像素通常聚合多个原始点，保存的 `point_ranges` 可以反查全部数据。

## 两个案例如何确定行窗口

| 案例 | 分行方法 | 局限 |
|---|---|---|
| Z字母 | 在给定周期范围内，寻找相邻图像行更一致的恒定周期和起点 | 偏好行间连续形状，不是真实同步轨迹 |
| 矩形框 | 用20个重复高平台作为往返的相位参照，插值为40行，首尾外推，每行两端各去3% | 平台不是到位信号，3%是估计，不能恢复行内变速 |

矩形框先用9点中值滤波寻找“大于64 μA且持续超过20点”的平台；滤波只用于分行参照。像素中位数仍使用原始电流，蓝黄分类阈值是全部原始数据的Otsu阈值，约30.426 μA。64 μA和30.426 μA的用途不同。

自动阈值从电流分布中分开两类，不读取照片。等待、换行等未用于图像的点保留在原始曲线中，反查行列标记为−1。

## 优先review哪里

1. [矩形框分行估计](../../experiments/tape-frame/prepare_windows.py)：核对相位假设和有效区间。
2. [简明入口](../../reconstruction/simple_reconstruct.py)：五步处理的串联。
3. [aggregate函数](../../reconstruction/snake_scan/pipeline.py)：像素分组与逐点对应。

按点数等分隐含采样均匀、横扫匀速。如果突然快移，相同点数覆盖的实际距离变大，等宽像素就会失真。下次记录真实行区间可以替换窗口估计；若要修复行内非匀速，还需要同步的位置轨迹和相应的空间分箱算法，当前例程没有实现。
