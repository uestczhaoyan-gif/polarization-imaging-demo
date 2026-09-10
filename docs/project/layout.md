# 目录与命名规范

根目录只保留README中英文版、LICENSE、一个 `START.cmd` 入口以及功能目录。安装依赖在各代码模块声明，维护文档统一放在 `docs/project/`，不在根目录叠加快捷脚本、发布包或实验文件。

## 职责

- `firmware/`：运行在STM32上的工程，保留厂商和Keil/CubeMX约定的目录。
- `tools/`：桌面工作台。它编辑固件配置，不直接控制硬件。
- `reconstruction/`：可复用Python代码和测试，不混放实测原文件。
- `experiments/`：两个同级实测案例与独立合成验证；每个案例有README、配置、原始数据和发布结果。
- `docs/`：`hardware/`、`reconstruction/`、`templates/`、`project/` 四类说明。
- `scripts/`：维护者检查、验证和发布脚本。
- `local/`：新生成结果、配置备份和临时实验；默认不上传。

自有目录和说明文件使用有意义的英文小写连字符名；Python模块用下划线。实验日期写在实验记录和README中，不把临时日期或“最终版”堆进目录名。矩形框的 `anchored/` 表示波形辅助分行结果，`uniform/` 表示固定周期对照，均放在该案例 `results/` 内。发布生成文件保持一致名称以便代码读取。

## v2 → v3 对照

| 旧位置 | 新位置 |
|---|---|
| `reconstruction/examples/z_tape/` | `experiments/tape-z/` |
| `reconstruction/results/z_tape/` | `experiments/tape-z/results/` |
| `reconstruction/examples/dark_80mm_20260909/` | `experiments/tape-frame/` |
| `reconstruction/results/dark_80mm_20260909/` | `experiments/tape-frame/results/` |
| `reconstruction/examples/synthetic/`、对应结果 | `experiments/synthetic/`、其 `results/` |
| `reconstruction/docs/` | `docs/reconstruction/` |
| 多个根目录和子目录CMD | 根目录 `START.cmd` |
| `reconstruction/outputs/` | `local/reconstruction/<案例>/` |

54个结果快照逐字节保留，原始测量数据不变。结果内嵌的旧路径和旧版本属于生成时记录，不批量改写；新位置的顶层JSON是当前可运行配置。Git历史保留迁移前版本。更新已有clone时，本地旧输出可能仍在原目录，它们不会被主动删除或发布。
