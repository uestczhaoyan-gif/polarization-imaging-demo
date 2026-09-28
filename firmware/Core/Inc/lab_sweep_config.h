#ifndef LAB_SWEEP_CONFIG_H
#define LAB_SWEEP_CONFIG_H
/* Generated finite table. Use the stage-test GUI to change it. */
#define LAB_SWEEP_KIND 4U
#define LAB_SWEEP_COUNT 9U
#define LAB_SWEEP_PULSES {320UL, 160UL, 64UL, 32UL, 16UL, 8UL, 4UL, 2UL, 1UL}
#define LAB_SWEEP_RPMS {60U, 60U, 60U, 60U, 60U, 60U, 60U, 60U, 60U}
#define LAB_SWEEP_PRELOAD_PULSES 640UL
#define LAB_SWEEP_PAUSE_MS 5000UL
#if LAB_EXPERIMENT >= 4U
#if LAB_EXPERIMENT != LAB_SWEEP_KIND
#error "Regenerate sweep table for selected experiment"
#endif
#if (1ULL * 1600UL * LEAD_UM_PER_REV > 1ULL * MOTOR_PULSES_PER_REV * ((LAB_TEST_AXIS == 0U) ? X_AXIS_MAX_SAFE_TRAVEL_UM : Y_AXIS_MAX_SAFE_TRAVEL_UM))
#error "Sweep exceeds declared travel"
#endif
#if (1ULL * 1120UL * LEAD_UM_PER_REV > 1ULL * MOTOR_PULSES_PER_REV * ((LAB_TEST_AXIS == 0U) ? X_AXIS_MAX_SAFE_TRAVEL_UM : Y_AXIS_MAX_SAFE_TRAVEL_UM))
#error "Sweep exceeds declared travel"
#endif
#if (1ULL * 832UL * LEAD_UM_PER_REV > 1ULL * MOTOR_PULSES_PER_REV * ((LAB_TEST_AXIS == 0U) ? X_AXIS_MAX_SAFE_TRAVEL_UM : Y_AXIS_MAX_SAFE_TRAVEL_UM))
#error "Sweep exceeds declared travel"
#endif
#if (1ULL * 736UL * LEAD_UM_PER_REV > 1ULL * MOTOR_PULSES_PER_REV * ((LAB_TEST_AXIS == 0U) ? X_AXIS_MAX_SAFE_TRAVEL_UM : Y_AXIS_MAX_SAFE_TRAVEL_UM))
#error "Sweep exceeds declared travel"
#endif
#if (1ULL * 688UL * LEAD_UM_PER_REV > 1ULL * MOTOR_PULSES_PER_REV * ((LAB_TEST_AXIS == 0U) ? X_AXIS_MAX_SAFE_TRAVEL_UM : Y_AXIS_MAX_SAFE_TRAVEL_UM))
#error "Sweep exceeds declared travel"
#endif
#if (1ULL * 664UL * LEAD_UM_PER_REV > 1ULL * MOTOR_PULSES_PER_REV * ((LAB_TEST_AXIS == 0U) ? X_AXIS_MAX_SAFE_TRAVEL_UM : Y_AXIS_MAX_SAFE_TRAVEL_UM))
#error "Sweep exceeds declared travel"
#endif
#if (1ULL * 652UL * LEAD_UM_PER_REV > 1ULL * MOTOR_PULSES_PER_REV * ((LAB_TEST_AXIS == 0U) ? X_AXIS_MAX_SAFE_TRAVEL_UM : Y_AXIS_MAX_SAFE_TRAVEL_UM))
#error "Sweep exceeds declared travel"
#endif
#if (1ULL * 646UL * LEAD_UM_PER_REV > 1ULL * MOTOR_PULSES_PER_REV * ((LAB_TEST_AXIS == 0U) ? X_AXIS_MAX_SAFE_TRAVEL_UM : Y_AXIS_MAX_SAFE_TRAVEL_UM))
#error "Sweep exceeds declared travel"
#endif
#if (1ULL * 643UL * LEAD_UM_PER_REV > 1ULL * MOTOR_PULSES_PER_REV * ((LAB_TEST_AXIS == 0U) ? X_AXIS_MAX_SAFE_TRAVEL_UM : Y_AXIS_MAX_SAFE_TRAVEL_UM))
#error "Sweep exceeds declared travel"
#endif
#if (MOTOR_PULSES_PER_REV != 3200UL) || (LEAD_UM_PER_REV != 1000UL) || (LAB_TEST_REPEATS != 3UL)
#error "Mechanics/repetitions changed: regenerate sweep table"
#endif
#endif
#endif
