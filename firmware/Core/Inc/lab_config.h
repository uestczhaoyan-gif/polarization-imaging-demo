#ifndef LAB_CONFIG_H
#define LAB_CONFIG_H
/* 0: normal scan; 1: scan with PC start gate; 2: one-axis round trips;
 * 3: legacy incremental steps; 4: displacement sweep;
 * 5: descending speed sweep; 6: ascending speed sweep. */
#define LAB_EXPERIMENT                 0U
#define LAB_LOG_ENABLE                 0U
#define LAB_TEST_AXIS                  0U /* 0=X, 1=Y */
#define LAB_TEST_DISTANCE_UM           1000UL
#define LAB_TEST_REPEATS               3UL
#define LAB_TEST_DWELL_MS              1000UL
/* Log transport: USART3 PB10 TX / PB11 RX, 115200 8N1, 3.3V USB-TTL. */
#if (LAB_EXPERIMENT > 6U) || (LAB_LOG_ENABLE > 1U) || (LAB_TEST_AXIS > 1U)
#error "Invalid lab mode, log enable or axis"
#endif
#if (LAB_EXPERIMENT == 1U) && (LAB_LOG_ENABLE != 1U)
#error "Timing experiment requires PC logging; stage tests may run offline"
#endif
#if (LAB_TEST_REPEATS < 1UL) || (LAB_TEST_REPEATS > 1000UL) || (LAB_TEST_DWELL_MS > 60000UL)
#error "Lab repetition/dwell outside supported range"
#endif
#if (LAB_EXPERIMENT == 2U) || (LAB_EXPERIMENT == 3U)
#if (LAB_TEST_DISTANCE_UM < 1UL) || ((1ULL * LAB_TEST_DISTANCE_UM * MOTOR_PULSES_PER_REV) % LEAD_UM_PER_REV)
#error "Test distance must be positive and exact whole pulses"
#endif
#define LAB_TEST_RANGE_UM (1ULL * LAB_TEST_DISTANCE_UM * ((LAB_EXPERIMENT == 3U) ? LAB_TEST_REPEATS : 1UL))
#if (LAB_TEST_RANGE_UM > ((LAB_TEST_AXIS == 0U) ? X_AXIS_MAX_SAFE_TRAVEL_UM : Y_AXIS_MAX_SAFE_TRAVEL_UM))
#error "Test exceeds user-declared safe travel"
#endif
#if (DISTANCE_PULSES(LAB_TEST_RANGE_UM) > 0xFFFFFFFFULL) || (MOVE_NOMINAL_MS(LAB_TEST_RANGE_UM) + 20000ULL > 0xFFFFFFFFULL)
#error "Test pulse count/timeout overflow"
#endif
#endif
#ifndef LAB_TEST_RANGE_UM
#define LAB_TEST_RANGE_UM LAB_TEST_DISTANCE_UM
#endif
#endif
