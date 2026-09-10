# 统一成像演示项目

统一仓库：`uestczhaoyan-gif/polarization-imaging-demo`。

- 以原 `stm32-zdt-xy-stage` 仓库为基础，保留其历史、固件与第三方声明，并将仓库更名为统一项目名。
- 初次合并将 `snake-scan-reconstruction` 的完整树放在 `reconstruction/`，保留其 Git 历史。v3进一步将代码、案例和文档归入相应目录；原始数据、结果与校验清单均保留。
- 硬件说明归入 `docs/hardware/`；重构文档保留在 `docs/reconstruction/`，避免数据/参数相对路径失效。
- 根目录提供中英文 README，详细文档保持中文。v3使用唯一的 `START.cmd` 工作台入口，目录规范见 [目录说明](layout.md)。
- 原重构仓库的代码、数据与 Git 历史均已迁入这里，不再独立维护；其 Git bundle、发布记录和三个版本的 ZIP 附件另有本地完整备份。统一项目不依赖原独立仓库。原控制仓库链接由 GitHub 重命名重定向到统一仓库。

本次合并未改变固件的 C/H、Keil 工程或重构算法。已报告的加速异常单独记录在 [排查文档](../hardware/motion-anomalies.md)，没有因目录合并而被标记为已修复。

重构子模块的早期版本和结果快照仍保留其自身版本号；统一项目从 v2.0.0 开始发布，两者是不同层级的版本。后续变化见 [更新记录](changelog.md)。
