# 实验三：平台三项自动测试

只测试 **最小有效位移、最低平稳速度、最高平稳速度**。默认离线运行，现有 DAP、供电和电机连接即可，不需要 USB转TTL。

双击本目录 `START.cmd`，选择测试、设置档位、生成独立工程。正式分档实验使用新工程的 `04_ACTUAL_SNAKE_RUN.uvprojx`；先用01/02核对通信和方向。

完整的实验设置、测量步骤、LED含义、编译运行及数据汇总见 **[操作说明](operation-guide.md)**。

预设：[最小位移](presets/minimum_distance.json) · [最低平稳速度](presets/minimum_speed.json) · [最高平稳速度](presets/maximum_speed.json)。界面下拉选择会载入这些默认档位，实际脉冲/RPM与顺序保存在生成的配置和测量表中。

自动执行不等于自动判定；位移需量具，平稳性需观察或录像。程序不会将空白表或未完成档位判成通过。
