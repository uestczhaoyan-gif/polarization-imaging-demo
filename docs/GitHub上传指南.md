# GitHub 上传指南

[返回项目首页](../README.md) · [发布验证记录](验证记录.md)

本文对应仓库名 **`stm32-zdt-xy-stage`**。推荐第一次使用 GitHub Desktop 完成上传；后半部分提供完整命令行方法，两种方法任选一种。

## 1. 确定要上传的文件夹

上传这个文件夹中的内容：

```text
D:\BaiduNetdiskDownload\ZDT_XS系列第二代闭环步进电机资料\GitHub发布版\stm32-zdt-xy-stage
```

如果将项目复制到别处，使用新路径。进入后应直接看到 `README.md`、`firmware`、`docs`、`LICENSE` 等文件。

仓库首页应直接显示 README；不要选择上一级“GitHub发布版”，也不要将整个项目 ZIP 作为唯一源码文件上传。原始带日期的目录与 ZIP 用于本地备份。

本目录已包含 `.gitignore`，会排除 Keil 的 `Build_*`、Objects、HEX、个人设置、压缩包及本地资料。`.gitattributes` 统一文本换行。Windows 文件管理器中注意保留这两个以点开头的文件。

## 2. 发布前检查

- 阅读 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)：ZDT 的两份协议文件仍需确认厂商公开再分发条件。保留上游版权和许可证。
- `LICENSE` 沿用 `Copyright (c) 2026 Contributors`。如希望署自己的名字或课题组名称，可把 `Contributors` 替换为实际署名，正文不变。
- 按[验证记录](验证记录.md)填入实际完成的编译和硬件测试；尚未验证的项目如实保留状态。预编译 HEX 必须与实际测试参数对应。

## 3. 方法 A：GitHub Desktop

### 第一步：登录

准备自己的 [GitHub 账号](https://github.com/)，安装并打开 [GitHub Desktop](https://desktop.github.com/)，按界面完成登录。首次设置 Git 作者时填写希望公开的姓名与邮箱；需要隐藏邮箱时，可使用 GitHub 账号设置提供的 noreply 邮箱。

### 第二步：初始化本地仓库

在项目目录的空白处右键打开终端，确认是 PowerShell。也可以先打开 PowerShell，再复制以下两条命令：

```powershell
Set-Location -LiteralPath 'D:\BaiduNetdiskDownload\ZDT_XS系列第二代闭环步进电机资料\GitHub发布版\stm32-zdt-xy-stage'
git init -q -b main
```

新下载的源码首次使用 Git 时需要这一步；目录已经包含有效 `.git` 时可跳过。`-q` 表示静默运行，命令成功时没有输出。可运行 `git status --short --branch` 检查状态。如果提示找不到 `git`，安装 [Git for Windows](https://git-scm.com/downloads/win) 并重新打开终端。本地初始化流程见 [GitHub 官方说明](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github)。

### 第三步：将本地项目加入 Desktop

打开 GitHub Desktop，选择 **File → Add Local Repository…**，点击 **Choose…**，选择第一节的 `stm32-zdt-xy-stage` 文件夹，再点击 **Add Repository**。见 [添加本地仓库的官方步骤](https://docs.github.com/en/desktop/adding-and-cloning-repositories/adding-a-repository-from-your-local-computer-to-github-desktop)。

### 第四步：检查文件并提交

在 **Changes** 页确认待提交内容包含：

```text
README.md
firmware/
docs/
LICENSE
THIRD_PARTY_NOTICES.md
CONTRIBUTING.md
CHANGELOG.md
.gitignore
.gitattributes
```

确认没有原始资料目录、`.idea`、本机调试配置和编译输出。左下角 Summary 可以填写：

```text
feat: add STM32 ZDT dual-axis stage controller
```

点击 **Commit to main**。Commit 是保存到本地 Git 历史，此时还没有上传。

### 第五步：发布到 GitHub

点击 **Publish repository**，填写：

| 字段 | 建议内容 |
|---|---|
| Name | `stm32-zdt-xy-stage` |
| Description | `STM32F103 双轴平移台蛇形扫描控制，适用于 ZDT X42S 闭环步进电机与偏振成像演示实验。` |
| Keep this code private | 公开分享时取消勾选 |
| Organization | 个人账号选择 None；课题组组织选择对应组织 |

检查后点击 **Publish Repository**。这一步创建远程仓库并上传提交。使用此方法时由 Desktop 创建仓库即可，无需事先在网页新建同名仓库。公开选项与发布流程见 [GitHub Desktop 官方说明](https://docs.github.com/en/desktop/adding-and-cloning-repositories/adding-an-existing-project-to-github-using-github-desktop)。

### 第六步：检查网页

在 Desktop 中选择 **Repository → View on GitHub**，核对：

1. 仓库为 Public，首页正确显示中文 README。
2. 打开接线、参数和固件说明，链接可跳转。
3. 打开 `firmware/MDK-ARM/`，能看到四个 `.uvprojx`。
4. 打开 `firmware/BSP/Emm_V5.c`，中文注释正常显示。
5. 通过绿色 **Code → Download ZIP** 下载一个副本，解压后按首次运行文档检查工程完整性。

可在仓库 About 设置描述和 Topics，例如 `stm32`、`stm32f103`、`stepper-motor`、`xy-stage`、`polarization-imaging`。

### 第七步：以后如何更新

在这个本地文件夹修改文件，打开 Desktop 的 Changes 检查差异，填写本次修改说明，**Commit to main → Push origin**。先确认修改内容，再提交和推送。不要每次更新都新建一个带日期的仓库；版本差异交给 Git 记录。

## 4. 方法 B：PowerShell 完整命令行

这一节适用于未按方法 A 上传的情况。先在 [GitHub 新建仓库页面](https://github.com/new)创建名为 `stm32-zdt-xy-stage` 的仓库，选择 Public，README、`.gitignore`、License 均不初始化，因为本地已经有这些文件。复制新仓库显示的 HTTPS 地址。该顺序依据 [GitHub 导入本地源码说明](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github)。

打开 PowerShell，逐段执行；遇到错误先处理，不要继续向下粘贴。

### 进入目录并初始化

```powershell
Set-Location -LiteralPath 'D:\BaiduNetdiskDownload\ZDT_XS系列第二代闭环步进电机资料\GitHub发布版\stm32-zdt-xy-stage'
git init -q -b main
```

设置本仓库的提交署名。下面两个示例值必须替换为自己的信息；若 Git 已配置署名，可跳过：

```powershell
git config user.name '你的名字或GitHub用户名'
git config user.email '你的提交邮箱'
```

### 查看并暂存

```powershell
git status --short
git add .
git diff --cached --stat
```

检查列表是否只有本项目文件。需要详细查看某个修改时执行 `git diff --cached`。

### 提交与关联远程

```powershell
git commit -m 'feat: add STM32 ZDT dual-axis stage controller'
```

将下面 URL 中的 `YOUR-USERNAME` 替换成自己的用户名或组织名，也可以直接粘贴 GitHub 给出的仓库 HTTPS 地址：

```powershell
git remote add origin 'https://github.com/YOUR-USERNAME/stm32-zdt-xy-stage.git'
git remote -v
git push -u origin main
```

按 Git 凭据管理器弹出的登录流程完成认证。上传结束后打开仓库网页，执行方法 A 第六步的检查。不要把 GitHub 密码或令牌写进项目文件。

### 后续更新

```powershell
git status --short
git add .
git diff --cached --stat
git commit -m 'docs: clarify stage wiring'
git push
```

提交说明按实际修改填写。

## 5. 发布可复现的版本

首次完成编译与实机验证后，可以创建 `v1.0.0` Release。仓库中的 [CHANGELOG.md](../CHANGELOG.md) 当前标注“发布准备”，整理日期为 2026-09-08；实际发布时再记录真实版本日期。

Release 说明建议包含：硬件型号、驱动器固件、编译器、扫描宽/高/行距/速度、验证结果与已知限制。GitHub 会为版本提供源码下载；若另附 HEX，注明它属于通信检查、运动测试还是正式扫描，并附上对应配置。运动固件复位后会自动启动，这一点应写在附件说明中。

图片使用自己的设备照片并放在 `docs/` 下的合适目录，通过相对链接插入说明。演示视频可以使用视频平台链接，避免将大视频写入普通源码历史。

## 6. 上传常见错误

| 提示或现象 | 处理方式 |
|---|---|
| `fatal: unknown write failure on standard output` | 先运行 `git status --short --branch`。若显示 `No commits yet on main` 或正常分支状态，仓库已初始化，可继续；若显示不是 Git 仓库，再使用 `git init -q -b main`。该报错涉及终端输出，不能仅凭报错认定初始化失败 |
| `not a git repository` | 确认当前目录是项目根目录，再运行初始化步骤 |
| `Author identity unknown` | 设置本仓库的 `user.name` 和 `user.email` |
| `remote origin already exists` | 先运行 `git remote -v`；只有确认地址写错时才用 `git remote set-url origin '正确地址'` |
| `src refspec main does not match any` | 检查首次 commit 是否成功、当前分支是否为 main |
| 推送被拒绝，远程已有 README 等提交 | 查看网页和本地历史，先确认远程内容；不要直接强制覆盖。首次上传按本文创建空仓库可避免这类冲突 |
| 只有 ZIP，没有目录和 README 展示 | 应提交解压后的文件树，而非把项目压缩包作为唯一文件 |
| 编译后出现许多待提交文件 | 核对 `.gitignore` 是否位于仓库根目录，以及这些文件是否此前已被跟踪 |
