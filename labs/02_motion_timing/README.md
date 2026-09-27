# 实验二：运动事件与相对时间

先读 [共用操作](../README.md)。本次只接 STM32 和电脑，不连接源表。双击本目录 `START.cmd`，生成、编译、烧录对应工程；启动收集器后再复位 STM32。

在包根目录也可以运行：

```powershell
python -m pip install pyserial
python tools/collect_motion.py --port COM7 --project . --output local/run01
```

COM7 替换为外接 USB-TTL 端口。输出目录必须未存在。输入 `g` 回车启动一轮；`!` 回车请求停止。程序先等待完整 `BOOT`，若没有看到提示，检查端口并复位。一次记录中途复位会报错，必须建立新记录。

## 输出事件具体是什么意思

| 事件 | 含义与局限 |
|---|---|
| MOVE_BEGIN | STM32 准备发一条位移命令；不是机械开始运动时刻 |
| ACK | 驱动器命令应答，值 2 为接受；不等于到位 |
| DRIVER_REACHED_RX | STM32 接收中断收到 FD/9F 到位通知，带接收时刻；仍有驱动内部、串口和中断延迟 |
| STATUS_QUERY / STATUS_REPLY | 查询驱动状态及返回；连续确认并经过名义行程时间后才允许下一段 |
| MOVE_END | 软件认定本段可结束，含轮询/保护延迟，不能当成精确的扫描结束时刻 |
| RUN_BEGIN / RUN_END | 一轮程序开始 / 完成 |
| MOTOR_RX_DROPPED | 电机应答快照被覆盖的累计次数；非零时自动分析拒绝把该轮视为有效测量，保留原始日志排查 |
| SYNC | 电脑发问后 STM32 回应，用于估计两个时钟的对应关系 |

事件包含运动编号、行号、轴地址、方向、距离及 STM32 毫秒时间；电脑另记 UTC 和单调时钟。有效 X 扫描 phase=5，Y=6，空返=9。单轴测试的 Y 空返也用 phase=9。

驱动器需支持并设置对应应答模式。原例程的 Receive 可用于命令确认；需要 FD/9F 的直接到位通知时用 **Both**（以你的驱动型号手册为准）。没有到位通知也能用轮询完成控制，但不能伪造 `DRIVER_REACHED_RX`。通知没有命令序号，所以异常/延迟/重复通知仍可能有歧义，不能据此认证机械位置。

## 与源表时间轴怎么对应

1. 收集器运行并收到 READY 后，先等一次时钟交换。源表开始采集，在电脑输入 `m 0` 回车，记录“源表时间约为 0 秒”的人工标记；**回车时刻包含操作延迟**。更好的办法是在源表显示一个已知采集时间时同步记录该时间，并录像检查延迟。只有真实知道的对应点才可填写。
2. 再输入 `g` 开始扫描。扫描结束后保持源表和收集器运行，输入例如 `m 1800.2`，数值必须是当时源表的实际采集时间，不能照抄示例。等下一次时钟交换，再 `q` 退出。起止标记应包围全部有效扫描。
3. 保存源表原始文件。若文件没有每点采集时间或可靠的时间轴，本工具只能给出运动的相对时间，**不能完成可靠的逐点源表对齐**；不能把不明单位的积分时间当成采样周期。
4. 将人工标记转换为 MCU↔源表时间锚点：

```powershell
python tools/map_clocks.py --sync local/run01/pc_sync.csv --marks local/run01/manual_marks.csv --output local/run01/anchors.csv
```

若你已从录像/硬件等方式测得对应关系，可直接提供 `mcu_s,meter_s` 两列 CSV，至少两点且包围全扫描。`map_clocks` 用串口往返中点拟合时钟；这只是估计，不是硬件同步。

5. 导出每行的时间窗口（示例假设启用 Both，起步延迟暂记 0 秒）：

```powershell
python tools/align_motion.py --events local/run01/events.csv --anchors local/run01/anchors.csv --window-source driver --start-latency-s 0 --accept-estimated-position --output local/run01/aligned
```

`--start-latency-s` 是 MOVE_BEGIN 到有效匀速扫描起点的已测/声明延迟，0 只是未校正近似；MOVE_BEGIN 本身先经串口输出再发送电机指令，存在数毫秒额外延迟。`driver` 使用到位通知；缺少/重复通知会拒绝。`nominal` 用指令距离/整数 RPM 推算时长，只接受 ACC=0，遇到卡顿或突然加速则位置模型不可靠。两种方法都假设行内匀速，不能校正未知真实轨迹。

6. 主项目的重构配置选 `mode: "time_windows"`、`row_windows_csv` 指向生成文件，同时使原始数据时间轴单位为秒、零点与锚点的 `meter_s` 一致。方向以首行正向为基准；如果首行物理上从右往左，增加 `--first-row-reverse`。单向扫描会自动排除空返和换行。

先保存连续电流图，再按需二值化。每像素仍由所在时间区间内的多个采样点聚合；事件提供分行依据，不直接测量每个像素的位置。人工标记误差、串口延迟、光斑、积分时间和滑台异常都应进入误差说明。两锚点拟合残差为零不代表同步精度为零。
