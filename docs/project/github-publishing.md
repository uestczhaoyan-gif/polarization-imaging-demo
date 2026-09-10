# 获取与更新统一项目

项目地址：[polarization-imaging-demo](https://github.com/uestczhaoyan-gif/polarization-imaging-demo)。硬件固件和 Python 重构已经放在同一仓库。

## 第一次下载

不使用 Git：在仓库页面选择 Code → Download ZIP，或下载 Releases 的完整包，解压后先看根目录 README。

使用 Git：

```bash
git clone https://github.com/uestczhaoyan-gif/polarization-imaging-demo.git
cd polarization-imaging-demo
```

根目录 `START.cmd` 打开参数与实验工作台。固件在 `firmware/`，Python代码在 `reconstruction/`，两个同级实测案例及其结果在 `experiments/`。

## 保存和上传自己的修改

```bash
git status
git diff
git add path/to/changed-file
git commit -m "Describe the change"
git push origin main
```

需要仓库写权限；外部贡献者可先 Fork 后提交 Pull Request。提交前保存实际扫描参数，说明改动目的和验证结果。不要把一次测量的板上参数与仓库默认值混淆。

Keil构建产物、Python缓存及 `local/` 默认忽略。随版本发布的正式结果保存在各实验的 `results/`，清单是 `experiments/manifest.sha256`；运行 `python scripts/build_results.py` 可更新正式快照，需核对数据来源与对应关系。发布前运行 `python scripts/check_project.py` 和 `python scripts/run_tests.py`。

## 获取后续更新

先用 `git status` 检查本地修改，再根据自己的工作流提交或妥善保存，然后：

```bash
git pull --ff-only
```

原 `stm32-zdt-xy-stage` 地址已通过 GitHub 重命名重定向至统一项目。已有控制器仓库可以更新远端：

```bash
git remote set-url origin https://github.com/uestczhaoyan-gif/polarization-imaging-demo.git
```

原重构仓库保留历史，后续使用此统一仓库；无需删除个人的旧数据或本地结果。
