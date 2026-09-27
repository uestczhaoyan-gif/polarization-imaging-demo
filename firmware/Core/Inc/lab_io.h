#ifndef LAB_IO_H
#define LAB_IO_H
#include <stdint.h>
#include <stdbool.h>
void Lab_Init(void);
void Lab_Event(const char *event, uint32_t value);
void Lab_Service(void);
void Lab_Delay(uint32_t ms);
bool Lab_WaitStart(void);
bool Lab_Aborted(void);
void Lab_Context(uint32_t move, uint32_t row, uint32_t phase,
                 uint32_t axis, uint32_t direction, uint32_t distance);
void Lab_MotorRx(const uint8_t *data, uint16_t length, uint32_t tick);
/* Used for reset/wrap checks in each log; milliseconds are MCU receive/send times,
 * never an assertion of exact physical movement onset/arrival. */
#endif
