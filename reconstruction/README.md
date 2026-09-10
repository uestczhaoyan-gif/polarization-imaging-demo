# 重构代码

本目录只放算法、命令行入口、依赖声明与测试。实测数据和结果统一放在 [experiments/](../experiments/README.md)，使用说明统一放在 [docs/reconstruction/](../docs/README.md)。下列命令均在项目根目录执行。

## 先读哪几个文件

| 文件 | 负责的事情 |
|---|---|
| [simple_reconstruct.py](simple_reconstruct.py) | 日常入口：读取 → 行窗口 → 像素分组 → 奇偶翻转 → 导出 |
| [snake_scan/pipeline.py](snake_scan/pipeline.py) 的 `aggregate` | 每像素取中位数并保存原始下标，是像素处理核心 |
| [snake_scan/core.py](snake_scan/core.py) | 原始文件读取、Otsu阈值和旧Z实验的周期估计 |
| [snake_scan/report.py](snake_scan/report.py) | 图像、CSV和离线HTML导出 |
| [reconstruct.py](reconstruct.py) | 完整命令行入口，支持时间窗、点窗口、固定周期和估计模式 |

[核心处理过程](../docs/reconstruction/core-process.md) 用短代码说明算法。画图和导出不需要日常修改。

## 运行

```bash
python -m pip install -r reconstruction/requirements.txt
python reconstruction/simple_reconstruct.py --config experiments/tape-frame/config.json
python reconstruction/reconstruct.py run --config experiments/tape-z/config.json --open
python reconstruction/reconstruct.py run --config experiments/synthetic/config.json
```

配置中的路径相对于配置文件；输出写到根目录 `local/reconstruction/`。完整入口再次运行同一输出目录需加 `--overwrite`。简明入口会更新自己配置的输出目录。

自己的数据可先运行 `python reconstruction/reconstruct.py wizard --output local/my-experiment/config.json`。完整模式与要求见 [参数说明](../docs/reconstruction/configuration.md)，输出各文件见 [结果说明](../docs/reconstruction/result-files.md)。

时间戳、行事件和实际参数应在采集时保存；电流积分时间不能直接当作采样间隔。按点等分要求采样均匀且横扫匀速，未知变速无法仅靠电流唯一恢复。两个实测例子均保留估计的不确定性，不按照片补画。

开发扩展见 [接口与测试](../docs/reconstruction/development.md)。重构模块历史版本见 [历史记录](../docs/project/reconstruction-history.md)；整个项目当前版本以根项目 Release 为准。
