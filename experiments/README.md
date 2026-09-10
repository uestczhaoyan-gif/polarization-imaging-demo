# 实验案例

两个实测案例按相同层级管理，每个案例的原始数据、配置、说明和结果放在一起。

| 文件夹 | 内容 | 入口 |
|---|---|---|
| `tape-z/` | 环境光下的胶带 Z 字母测量 | [案例说明](tape-z/README.md) |
| `tape-frame/` | 暗环境下的矩形胶带框测量 | [案例说明](tape-frame/README.md) |
| `synthetic/` | 具有已知答案的合成验证，不是测量 | [案例说明](synthetic/README.md) |

`data/` 保存测量原文件，JSON保存参数，`results/` 保存发布快照；重新运行写入根目录 `local/reconstruction/`。案例自用的分析脚本保留在案例中，通用算法在 `reconstruction/`。

[manifest.sha256](manifest.sha256) 覆盖全部54个发布结果文件，路径相对此目录。v3目录调整保留结果字节不变；历史结果元数据里仍可能出现生成时的旧路径，它们是历史记录，重算请使用各案例顶层的新配置。
