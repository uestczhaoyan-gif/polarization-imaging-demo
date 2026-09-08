#ifndef __SNAKE_SCAN_CONFIG_H
#define __SNAKE_SCAN_CONFIG_H

/*
 * 双轴掩模版蛇形扫描参数
 *
 * 日常更换掩模版时，只修改“1. 用户常用参数”中的数值。
 * 协议收发、脉冲换算和超时参数通常不需要修改。
 */

/* ========================================================================== */
/* 1. 用户常用参数：更换掩模版时优先只改这一段                           */
/* ========================================================================== */

/*
 * 掩模版的水平扫描宽度和垂直扫描高度，单位均为毫米。
 *
 * 示例：
 *   100 mm x 100 mm：宽度=100，高度=100
 *   100 mm x  50 mm：宽度=100，高度= 50
 *    50 mm x 100 mm：宽度= 50，高度=100
 */
#define MASK_SCAN_WIDTH_MM                 100UL
#define MASK_SCAN_HEIGHT_MM                100UL

/*
 * 相邻两条水平扫描线之间的垂直距离，单位毫米。
 * 当前为2 mm。掩模版高度必须能被该数值整除。
 */
#define SCAN_LINE_STEP_MM                  2UL

/* 扫描线速度：1000 um/s = 1.000 mm/s。 */
#define SCAN_SPEED_UM_PER_SEC              1000UL

/*
 * 电机方向原始值：0=CW，1=CCW。
 * 第一条水平扫描线使用方向1，第二条使用方向0，之后逐条交替。
 * 如果以后机械安装方向发生变化，只交换下面两个值，不要交换电机地址。
 */
#define X_FIRST_PASS_DIRECTION             1U
#define X_ALTERNATE_PASS_DIRECTION         0U

/* 垂直轴每完成一条水平线后向上移动的方向值。 */
#define Y_STEP_DIRECTION                    0U

/*
 * 软件安全行程，必须不大于机械实际可用行程。
 * 程序会在编译时阻止掩模版宽度或高度超过这些数值。
 */
#define X_AXIS_MAX_SAFE_TRAVEL_MM          100UL
#define Y_AXIS_MAX_SAFE_TRAVEL_MM          100UL

/* ========================================================================== */
/* 2. 电机、丝杆和通信参数：硬件不变时不要修改                               */
/* ========================================================================== */

/* 水平滑轨地址2，垂直滑轨地址1。 */
#define X_AXIS_ADDR                         2U
#define Y_AXIS_ADDR                         1U

/* 1.8度电机每圈200整步；0.9度电机应改为400。 */
#define MOTOR_FULL_STEPS_PER_REV            200UL

/* 必须与两台驱动器菜单中的MStep一致；当前为16细分。 */
#define MOTOR_MICROSTEP                     16UL

/* T6x1丝杆：每转移动1.000 mm，即1000 um/rev。 */
#define LEAD_UM_PER_REV                     1000UL

/* Emm加速度：0表示不使用加减速曲线，直接按设定速度启动。 */
#define SCAN_ACCELERATION                   0U

/*
 * 一次性地址设置：
 * 1 = 仅连接待设置的垂直电机，把出厂地址1写成Y_AXIS_ADDR；
 * 0 = 正常运行。完成一次地址设置后必须恢复为0。
 */
#define Y_AXIS_ID_SETUP_ONCE                0U

/*
 * 1 = 上电通信成功后清零两台驱动器内部位置计数；0 = 不清零。
 * 这不是机械回零。没有限位/原点传感器时通常保持0。
 */
#define RESET_MOTOR_COUNTERS_AT_START       0U

/* ========================================================================== */
/* 3. 可直接编译下载的四个阶段：通常无需修改                                 */
/* ========================================================================== */

#define SCAN_STAGE_COMM_CHECK               0U  /* 只检查地址，不运动 */
#define SCAN_STAGE_1MM_TEST                 1U  /* X每次1 mm，Y每次1 mm，共2条线 */
#define SCAN_STAGE_10MM_TEST                2U  /* X每次10 mm，Y每次2 mm，共2条线 */
#define SCAN_STAGE_ACTUAL_RUN               3U  /* 使用上面的掩模版参数 */

#ifndef SCAN_STAGE
#define SCAN_STAGE                          SCAN_STAGE_COMM_CHECK
#endif

#if (SCAN_STAGE == SCAN_STAGE_COMM_CHECK)
#define ACTIVE_SCAN_WIDTH_MM                1UL
#define ACTIVE_SCAN_HEIGHT_MM               1UL
#define ACTIVE_LINE_STEP_MM                 1UL
#elif (SCAN_STAGE == SCAN_STAGE_1MM_TEST)
#define ACTIVE_SCAN_WIDTH_MM                1UL
#define ACTIVE_SCAN_HEIGHT_MM               2UL
#define ACTIVE_LINE_STEP_MM                 1UL
#elif (SCAN_STAGE == SCAN_STAGE_10MM_TEST)
#define ACTIVE_SCAN_WIDTH_MM                10UL
#define ACTIVE_SCAN_HEIGHT_MM               4UL
#define ACTIVE_LINE_STEP_MM                 2UL
#elif (SCAN_STAGE == SCAN_STAGE_ACTUAL_RUN)
#define ACTIVE_SCAN_WIDTH_MM                MASK_SCAN_WIDTH_MM
#define ACTIVE_SCAN_HEIGHT_MM               MASK_SCAN_HEIGHT_MM
#define ACTIVE_LINE_STEP_MM                 SCAN_LINE_STEP_MM
#else
#error "SCAN_STAGE must be one of the four SCAN_STAGE_* values"
#endif

/*
 * 每完成一条水平扫描线，Y轴移动一次。因此：
 * 水平扫描线数量 = 掩模版高度 / 行距。
 * 100x50 mm、行距2 mm时执行25条水平线。
 */
#define ACTIVE_HORIZONTAL_PASS_COUNT        \
        (ACTIVE_SCAN_HEIGHT_MM / ACTIVE_LINE_STEP_MM)

/* ========================================================================== */
/* 4. 自动换算和通信容错参数：不建议修改                                     */
/* ========================================================================== */

#define MOTOR_PULSES_PER_REV                \
        (MOTOR_FULL_STEPS_PER_REV * MOTOR_MICROSTEP)
#define PULSES_PER_MM                       \
        ((MOTOR_PULSES_PER_REV * 1000UL) / LEAD_UM_PER_REV)
#define SCAN_SPEED_RPM                      \
        (((SCAN_SPEED_UM_PER_SEC * 60UL) + (LEAD_UM_PER_REV / 2UL)) / \
         LEAD_UM_PER_REV)

#define MOTOR_REPLY_TIMEOUT_MS              500UL
#define MOTOR_COMM_RETRY_COUNT              3U
#define MOTOR_COMM_RETRY_DELAY_MS           50UL
#define STATUS_POLL_INTERVAL_MS             500UL
#define AXIS_SWITCH_DELAY_MS                300UL
#define SCAN_START_COUNTDOWN_SECONDS        5U

#define X_MOVE_TIMEOUT_MS                   \
        (((ACTIVE_SCAN_WIDTH_MM * 1000000UL) / SCAN_SPEED_UM_PER_SEC) + 20000UL)
#define Y_MOVE_TIMEOUT_MS                   \
        (((ACTIVE_LINE_STEP_MM * 1000000UL) / SCAN_SPEED_UM_PER_SEC) + 4000UL)

/* ========================================================================== */
/* 5. 编译期安全检查：参数不合理时直接阻止生成固件                            */
/* ========================================================================== */

#if (MASK_SCAN_WIDTH_MM == 0UL)
#error "MASK_SCAN_WIDTH_MM must be greater than zero"
#endif

#if (MASK_SCAN_HEIGHT_MM == 0UL)
#error "MASK_SCAN_HEIGHT_MM must be greater than zero"
#endif

#if (SCAN_LINE_STEP_MM == 0UL)
#error "SCAN_LINE_STEP_MM must be greater than zero"
#endif

#if ((MASK_SCAN_HEIGHT_MM % SCAN_LINE_STEP_MM) != 0UL)
#error "MASK_SCAN_HEIGHT_MM must be divisible by SCAN_LINE_STEP_MM"
#endif

#if (MASK_SCAN_WIDTH_MM > X_AXIS_MAX_SAFE_TRAVEL_MM)
#error "Mask width exceeds X_AXIS_MAX_SAFE_TRAVEL_MM"
#endif

#if (MASK_SCAN_HEIGHT_MM > Y_AXIS_MAX_SAFE_TRAVEL_MM)
#error "Mask height exceeds Y_AXIS_MAX_SAFE_TRAVEL_MM"
#endif

#if (MOTOR_FULL_STEPS_PER_REV == 0UL)
#error "MOTOR_FULL_STEPS_PER_REV must be greater than zero"
#endif

#if ((MOTOR_MICROSTEP == 0UL) || (MOTOR_MICROSTEP > 256UL))
#error "MOTOR_MICROSTEP must be in the driver range 1..256"
#endif

#if (LEAD_UM_PER_REV == 0UL)
#error "LEAD_UM_PER_REV must be greater than zero"
#endif

#if (SCAN_SPEED_UM_PER_SEC == 0UL)
#error "SCAN_SPEED_UM_PER_SEC must be greater than zero"
#endif

#if (((MOTOR_PULSES_PER_REV * 1000UL) % LEAD_UM_PER_REV) != 0UL)
#error "Configured lead does not produce an integer pulse count per millimeter"
#endif

#if ((X_FIRST_PASS_DIRECTION > 1U) || (X_ALTERNATE_PASS_DIRECTION > 1U) || \
     (Y_STEP_DIRECTION > 1U))
#error "Motor direction values must be 0 or 1"
#endif

#if (X_FIRST_PASS_DIRECTION == X_ALTERNATE_PASS_DIRECTION)
#error "The two horizontal pass directions must be different"
#endif

#if (ACTIVE_HORIZONTAL_PASS_COUNT == 0UL)
#error "The selected stage must contain at least one horizontal pass"
#endif

#if (SCAN_SPEED_RPM == 0UL)
#error "Configured linear speed rounds to 0 RPM"
#endif

#if (SCAN_SPEED_RPM > 3000UL)
#error "Configured linear speed exceeds the Emm 3000 RPM command limit"
#endif

#if (MOTOR_COMM_RETRY_COUNT == 0U)
#error "MOTOR_COMM_RETRY_COUNT must be greater than zero"
#endif

#endif /* __SNAKE_SCAN_CONFIG_H */
